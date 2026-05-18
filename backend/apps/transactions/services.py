"""Transaction services — Conversion Engine + Payment Engine"""
import uuid
import logging
from decimal import Decimal
from django.db import transaction

from core.exceptions import InsufficientBalanceError, ExchangeRateUnavailableError, TransactionError
from apps.wallet.models import CurrencyChoice
from apps.wallet.services import WalletService
from apps.exchange.services import RateService
from .models import ConversionHistory, PaymentTransaction

logger = logging.getLogger("nexuspay")


class ConversionService:

    @staticmethod
    @transaction.atomic
    def convert(user, from_currency: str, to_currency: str, amount: Decimal) -> ConversionHistory:
        """Atomic USDT↔INR conversion with ledger records"""
        wallet = WalletService.get_wallet(user)
        rate_obj = RateService.get_current_rate("USDT_INR")
        if not rate_obj:
            raise ExchangeRateUnavailableError()

        quote = RateService.calculate_conversion(from_currency, to_currency, amount, rate_obj)
        reference_id = f"CONV-{uuid.uuid4().hex[:12].upper()}"

        # Create conversion record
        conversion = ConversionHistory.objects.create(
            user=user,
            wallet=wallet,
            from_currency=from_currency,
            to_currency=to_currency,
            from_amount=amount,
            to_amount=quote["to_amount"],
            rate=quote["rate"],
            gross_amount=quote["gross_amount"],
            fee_amount=quote["fee_amount"],
            spread_percent=Decimal(str(quote["spread_percent"])),
            fee_percent=Decimal(str(quote["fee_percent"])),
            status="PENDING",
            reference_id=reference_id,
            exchange_rate_id=rate_obj.id,
        )

        try:
            # Step 1: Debit source currency
            debit_tx = WalletService.debit(
                wallet=wallet,
                currency=from_currency,
                amount=amount,
                category="CONVERSION",
                description=f"Convert {amount} {from_currency} → {to_currency}",
                reference_id=f"DEBIT-{reference_id}",
                metadata={"conversion_id": str(conversion.id)},
                actor=user,
            )

            # Step 2: Credit target currency
            credit_tx = WalletService.credit(
                wallet=wallet,
                currency=to_currency,
                amount=quote["to_amount"],
                category="CONVERSION",
                description=f"Received {quote['to_amount']} {to_currency} from conversion",
                reference_id=f"CREDIT-{reference_id}",
                metadata={"conversion_id": str(conversion.id)},
                actor=user,
            )

            # Update conversion record
            conversion.status = "COMPLETED"
            conversion.debit_tx = debit_tx.id
            conversion.credit_tx = credit_tx.id
            conversion.save(update_fields=["status", "debit_tx", "credit_tx", "updated_at"])

            logger.info(f"[CONVERSION] {amount} {from_currency} → {quote['to_amount']} {to_currency} | ref={reference_id}")

        except Exception as e:
            conversion.status = "FAILED"
            conversion.save(update_fields=["status", "updated_at"])
            logger.error(f"[CONVERSION FAILED] {reference_id}: {e}")
            raise TransactionError(f"Conversion failed: {str(e)}")

        return conversion


class PaymentService:

    @staticmethod
    @transaction.atomic
    def process_payment(
        user,
        merchant_name: str,
        amount_inr: Decimal,
        description: str = "",
        merchant_category: str = "General",
    ) -> PaymentTransaction:
        """
        Smart payment engine:
        1. Use available INR balance first
        2. If insufficient, convert required USDT amount to INR on-the-fly
        3. Complete payment with combined balance
        """
        wallet = WalletService.get_wallet(user)
        reference_id = f"PAY-{uuid.uuid4().hex[:12].upper()}"

        inr_balance = wallet.inr_balance
        inr_from_balance = Decimal("0.00")
        usdt_converted = Decimal("0.00000000")
        inr_from_conversion = Decimal("0.00")
        related_conversion = None
        conversion_rate = None

        if inr_balance >= amount_inr:
            # Pay entirely from INR balance
            inr_from_balance = amount_inr
        else:
            # Use all available INR + convert required USDT
            inr_from_balance = inr_balance
            inr_needed = amount_inr - inr_balance

            rate_obj = RateService.get_current_rate("USDT_INR")
            if not rate_obj:
                raise ExchangeRateUnavailableError()

            # How much USDT needed to get inr_needed after spread/fee?
            quote = RateService.calculate_conversion("USDT", "INR", Decimal("1"), rate_obj)
            effective_rate = quote["to_amount"]  # INR per 1 USDT after spread/fee

            usdt_required = (inr_needed / effective_rate).quantize(Decimal("0.00000001"))
            # Add 1% buffer for rounding
            usdt_required = usdt_required * Decimal("1.01")

            if wallet.usdt_balance < usdt_required:
                raise InsufficientBalanceError(
                    f"Insufficient balance. Need ₹{amount_inr}, have ₹{inr_balance} INR "
                    f"and ${wallet.usdt_balance} USDT (need ~${usdt_required} USDT more)"
                )

            # Convert USDT → INR
            related_conversion = ConversionService.convert(user, "USDT", "INR", usdt_required)
            inr_from_conversion = related_conversion.to_amount
            usdt_converted = usdt_required
            conversion_rate = rate_obj.sell_rate

            # Refresh wallet after conversion
            wallet.refresh_from_db()

        # Create payment record
        payment = PaymentTransaction.objects.create(
            user=user,
            wallet=wallet,
            merchant_name=merchant_name,
            merchant_category=merchant_category,
            amount_inr=amount_inr,
            inr_from_balance=inr_from_balance,
            usdt_converted=usdt_converted,
            inr_from_conversion=inr_from_conversion,
            conversion_rate=conversion_rate,
            description=description or f"Payment to {merchant_name}",
            status="PENDING",
            reference_id=reference_id,
            related_conversion=related_conversion,
        )

        try:
            # Debit total INR
            wallet_tx = WalletService.debit(
                wallet=wallet,
                currency="INR",
                amount=amount_inr,
                category="PAYMENT",
                description=f"Payment to {merchant_name}",
                reference_id=f"DEBIT-{reference_id}",
                metadata={"payment_id": str(payment.id)},
                actor=user,
            )

            payment.status = "COMPLETED"
            payment.wallet_tx = wallet_tx.id
            payment.save(update_fields=["status", "wallet_tx"])

            logger.info(f"[PAYMENT] ₹{amount_inr} → {merchant_name} | ref={reference_id}")

        except Exception as e:
            payment.status = "FAILED"
            payment.save(update_fields=["status"])
            logger.error(f"[PAYMENT FAILED] {reference_id}: {e}")
            raise TransactionError(f"Payment failed: {str(e)}")

        return payment
