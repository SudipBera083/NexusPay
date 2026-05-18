"""Transaction services — Conversion Engine + Payment Engine"""
import uuid
import logging
from decimal import Decimal
from django.db import transaction

from core.exceptions import InsufficientBalanceError, ExchangeRateUnavailableError, TransactionError
from apps.wallet.models import CurrencyChoice, WalletType
from apps.wallet.services import WalletService
from apps.exchange.services import RateService
from .models import ConversionHistory, PaymentTransaction, Merchant

logger = logging.getLogger("nexuspay")


class ConversionService:

    @staticmethod
    @transaction.atomic
    def convert(user, from_currency: str, to_currency: str, amount: Decimal) -> ConversionHistory:
        """Atomic USDT↔INR conversion routing via Treasury wallets"""
        user_wallet = WalletService.get_wallet(user)
        rate_obj = RateService.get_current_rate("USDT_INR")
        if not rate_obj:
            raise ExchangeRateUnavailableError()

        quote = RateService.calculate_conversion(from_currency, to_currency, amount, rate_obj)
        reference_id = f"CONV-{uuid.uuid4().hex[:12].upper()}"

        # Initialize Conversion Record
        conversion = ConversionHistory.objects.create(
            user=user,
            wallet=user_wallet,
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
            # Get Treasury Wallets
            treasury_inr = WalletService.get_treasury_wallet(WalletType.TREASURY_RESERVE_INR)
            treasury_usdt = WalletService.get_treasury_wallet(WalletType.TREASURY_RESERVE_USDT)
            treasury_fees = WalletService.get_treasury_wallet(WalletType.TREASURY_FEES)

            # Double-Entry Transfer 1: User pays source currency to Treasury
            source_treasury = treasury_inr if from_currency == "INR" else treasury_usdt
            journal_1 = WalletService.transfer(
                from_wallet=user_wallet,
                to_wallet=source_treasury,
                currency=from_currency,
                amount=amount,
                category="CONVERSION",
                description=f"Convert {amount} {from_currency} → {to_currency} (Leg 1)",
                reference_id=f"LEG1-{reference_id}",
                idempotency_key=f"LEG1-{reference_id}",
                actor=user,
            )

            # Double-Entry Transfer 2: Treasury pays target currency to User
            target_treasury = treasury_inr if to_currency == "INR" else treasury_usdt
            journal_2 = WalletService.transfer(
                from_wallet=target_treasury,
                to_wallet=user_wallet,
                currency=to_currency,
                amount=quote["to_amount"],
                category="CONVERSION",
                description=f"Received {quote['to_amount']} {to_currency} from conversion (Leg 2)",
                reference_id=f"LEG2-{reference_id}",
                idempotency_key=f"LEG2-{reference_id}",
                actor=user,
            )

            # Double-Entry Transfer 3: Treasury pays Fee to Treasury Fees Wallet
            fee_currency = from_currency  # Usually fee is taken from the source currency side in the treasury backend
            fee_journal = None
            if quote["fee_amount"] > Decimal("0"):
                fee_journal = WalletService.transfer(
                    from_wallet=source_treasury,
                    to_wallet=treasury_fees,
                    currency=fee_currency,
                    amount=quote["fee_amount"],
                    category="FEE",
                    description=f"Conversion fee for {reference_id}",
                    reference_id=f"FEE-{reference_id}",
                    idempotency_key=f"FEE-{reference_id}",
                )

            # Update conversion record with journal links in metadata
            conversion.status = "COMPLETED"
            conversion.metadata = {
                "leg1_journal_id": str(journal_1.id),
                "leg2_journal_id": str(journal_2.id),
                "fee_journal_id": str(fee_journal.id) if fee_journal else None,
            }
            conversion.save(update_fields=["status", "metadata", "updated_at"])

            logger.info(f"[CONVERSION] {amount} {from_currency} → {quote['to_amount']} {to_currency} via Treasury")

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
        idempotency_key: str = None,
    ) -> PaymentTransaction:
        """
        Smart payment engine with Double-Entry Merchant settlement.
        """
        if idempotency_key:
            existing = PaymentTransaction.objects.filter(metadata__idempotency_key=idempotency_key).first()
            if existing:
                return existing

        wallet = WalletService.get_wallet(user)
        reference_id = f"PAY-{uuid.uuid4().hex[:12].upper()}"

        # 1. Get or Create Merchant
        merchant, _ = Merchant.objects.get_or_create(
            name=merchant_name,
            defaults={"category": merchant_category}
        )
        if not hasattr(merchant, 'merchant_profile') or not merchant.wallet:
            merchant_wallet = WalletService.get_treasury_wallet(WalletType.MERCHANT)
            merchant.wallet = merchant_wallet
            merchant.save()
        else:
            merchant_wallet = merchant.wallet

        inr_balance = wallet.inr_balance
        inr_from_balance = Decimal("0.00")
        usdt_converted = Decimal("0.00000000")
        inr_from_conversion = Decimal("0.00")
        related_conversion = None
        conversion_rate = None

        # 2. Check Balances & Auto-Convert if needed
        if inr_balance >= amount_inr:
            inr_from_balance = amount_inr
        else:
            inr_from_balance = inr_balance
            inr_needed = amount_inr - inr_balance

            rate_obj = RateService.get_current_rate("USDT_INR")
            if not rate_obj:
                raise ExchangeRateUnavailableError()

            quote = RateService.calculate_conversion("USDT", "INR", Decimal("1"), rate_obj)
            effective_rate = quote["to_amount"]

            usdt_required = (inr_needed / effective_rate).quantize(Decimal("0.00000001"))
            usdt_required = usdt_required * Decimal("1.01")  # 1% buffer

            if wallet.usdt_balance < usdt_required:
                raise InsufficientBalanceError(
                    f"Insufficient balance. Need ₹{amount_inr}, have ₹{inr_balance} INR "
                    f"and ${wallet.usdt_balance} USDT (need ~${usdt_required} USDT more)"
                )

            related_conversion = ConversionService.convert(user, "USDT", "INR", usdt_required)
            inr_from_conversion = related_conversion.to_amount
            usdt_converted = usdt_required
            conversion_rate = rate_obj.sell_rate

            wallet.refresh_from_db()

        # 3. Create Payment Record
        payment = PaymentTransaction.objects.create(
            user=user,
            wallet=wallet,
            merchant=merchant,
            amount_inr=amount_inr,
            inr_from_balance=inr_from_balance,
            usdt_converted=usdt_converted,
            inr_from_conversion=inr_from_conversion,
            conversion_rate=conversion_rate,
            description=description or f"Payment to {merchant_name}",
            status="PENDING",
            reference_id=reference_id,
            related_conversion=related_conversion,
            metadata={"idempotency_key": idempotency_key} if idempotency_key else {}
        )

        try:
            # 4. Double-Entry Transfer: User Wallet -> Merchant Wallet
            journal = WalletService.transfer(
                from_wallet=wallet,
                to_wallet=merchant_wallet,
                currency="INR",
                amount=amount_inr,
                category="PAYMENT",
                description=f"Payment to {merchant.name}",
                reference_id=f"PAY-{reference_id}",
                idempotency_key=f"PAY-{reference_id}",
                actor=user,
            )

            payment.status = "COMPLETED"
            payment.metadata["journal_id"] = str(journal.id)
            payment.save(update_fields=["status", "metadata"])

            logger.info(f"[PAYMENT] ₹{amount_inr} → {merchant.name} | ref={reference_id}")

        except Exception as e:
            payment.status = "FAILED"
            payment.save(update_fields=["status"])
            logger.error(f"[PAYMENT FAILED] {reference_id}: {e}")
            raise TransactionError(f"Payment failed: {str(e)}")

        return payment
