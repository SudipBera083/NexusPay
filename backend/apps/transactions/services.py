"""Transaction services — Conversion Engine + Payment Engine"""
import uuid
import logging
from decimal import Decimal
from django.db import transaction

from core.exceptions import InsufficientBalanceError, ExchangeRateUnavailableError, TransactionError
from apps.wallet.models import CurrencyChoice, WalletType
from apps.wallet.services import WalletService
from apps.exchange.services import RateService
from .models import ConversionHistory, PaymentTransaction, PaymentStatus
from apps.merchants.models import Merchant, MerchantQRCode, QRCodeStatus

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
    def initiate_qr_payment(
        user,
        qr_nonce: str,
        idempotency_key: str = None,
    ) -> PaymentTransaction:
        """
        Step 1: User scans a QR code and initiates payment.
        Validates QR and creates PaymentTransaction in CREATED state.
        """
        try:
            qr_code = MerchantQRCode.objects.select_related("merchant").get(nonce=qr_nonce)
        except MerchantQRCode.DoesNotExist:
            raise ValueError("QR code not found")

        if qr_code.is_expired:
            raise ValueError("QR code is expired")
            
        if qr_code.is_consumed:
            raise ValueError("QR code has already been consumed")

        if idempotency_key:
            existing = PaymentTransaction.objects.filter(metadata__idempotency_key=idempotency_key).first()
            if existing:
                return existing

        wallet = WalletService.get_wallet(user)
        reference_id = f"PAY-{uuid.uuid4().hex[:12].upper()}"

        amount_usdc = qr_code.amount_usdc
        merchant = qr_code.merchant

        payment = PaymentTransaction.objects.create(
            user=user,
            wallet=wallet,
            merchant=merchant,
            amount_inr=Decimal("0.00"),
            inr_from_balance=Decimal("0.00"),
            usdt_converted=amount_usdc,
            inr_from_conversion=Decimal("0.00"),
            conversion_rate=Decimal("0.00"),
            description=f"Web3 Payment to {merchant.name}",
            status=PaymentStatus.CREATED,
            reference_id=reference_id,
            qr_code=qr_code,
            metadata={"idempotency_key": idempotency_key} if idempotency_key else {}
        )
        
        qr_code.created_for_user = user
        qr_code.save(update_fields=["created_for_user"])

        return payment

    @staticmethod
    @transaction.atomic
    def submit_blockchain_signature(
        payment_id: str,
        user,
        tx_hash: str,
        wallet_address: str,
    ) -> PaymentTransaction:
        """
        Step 2: User signed and broadcasted the transaction via MetaMask.
        We link the tx_hash to the PaymentTransaction and transition to SUBMITTED.
        """
        try:
            payment = PaymentTransaction.objects.select_related("qr_code").get(id=payment_id)
        except PaymentTransaction.DoesNotExist:
            raise ValueError("Payment not found")

        if payment.user != user:
            raise PermissionError("Payment does not belong to this user")

        if payment.status != PaymentStatus.CREATED:
            raise ValueError(f"Cannot submit signature for payment in state: {payment.status}")

        # Basic anti-spoof check (the indexer will strictly verify the on-chain sender)
        if payment.wallet.web3_address and payment.wallet.web3_address.lower() != wallet_address.lower():
            logger.warning(f"Wallet mismatch. DB: {payment.wallet.web3_address}, Provided: {wallet_address}")
            # We don't block here because users might use a different linked wallet,
            # but the indexer will verify if the on-chain sender is authorized.

        # Ensure unique tx_hash globally to prevent replay/duplicate settlement
        if PaymentTransaction.objects.filter(blockchain_tx_hash=tx_hash).exists():
            raise ValueError("Transaction hash already submitted for another payment")

        payment.blockchain_tx_hash = tx_hash
        payment.save(update_fields=["blockchain_tx_hash"])
        payment.transition_to(PaymentStatus.SUBMITTED)
        
        qr_code = payment.qr_code
        if qr_code:
            qr_code.blockchain_tx_hash = tx_hash
            qr_code.save(update_fields=["blockchain_tx_hash"])

        logger.info(f"[PAYMENT] {payment_id} submitted to blockchain: {tx_hash}")
        return payment

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
        Legacy INR payment flow: debit from user wallet directly to a shadow merchant.
        Creates or retrieves a shadow Merchant by name for tracking purposes.
        """
        from apps.merchants.models import Merchant, MerchantStatus
        from apps.wallet.models import WalletType

        wallet = WalletService.get_wallet(user)

        # Idempotency check
        if idempotency_key:
            existing = PaymentTransaction.objects.filter(metadata__idempotency_key=idempotency_key).first()
            if existing:
                return existing

        # Check balance
        if wallet.inr_balance < amount_inr:
            raise InsufficientBalanceError(
                f"Insufficient INR balance. Available: ₹{wallet.inr_balance}, Required: ₹{amount_inr}"
            )

        # Generate deterministic unique placeholder EVM address from merchant name
        import hashlib
        name_hash = hashlib.sha256(merchant_name.lower().encode()).hexdigest()[:40]
        placeholder_address = f"0x{name_hash}"

        # Get or create shadow merchant — unique by name only
        # Each shadow merchant gets its own MERCHANT-type wallet (OneToOneField requirement)
        try:
            merchant = Merchant.objects.get(name=merchant_name)
            merchant_wallet = merchant.internal_wallet or WalletService.get_treasury_wallet(WalletType.TREASURY_SETTLEMENT)
        except Merchant.DoesNotExist:
            from apps.wallet.models import Wallet as WalletModel
            merchant_wallet = WalletModel.objects.create(
                type=WalletType.MERCHANT,
                label=f"Shadow wallet — {merchant_name}",
            )
            merchant = Merchant.objects.create(
                name=merchant_name,
                user=None,
                wallet_address=placeholder_address,
                internal_wallet=merchant_wallet,
                status=MerchantStatus.ACTIVE,
            )

        reference_id = f"PAY-{uuid.uuid4().hex[:12].upper()}"

        payment = PaymentTransaction.objects.create(
            user=user,
            wallet=wallet,
            merchant=merchant,
            amount_inr=amount_inr,
            inr_from_balance=amount_inr,
            usdt_converted=Decimal("0.00"),
            inr_from_conversion=Decimal("0.00"),
            description=description or f"Payment to {merchant_name}",
            status=PaymentStatus.CONFIRMED,  # INR payments settle immediately
            reference_id=reference_id,
            metadata={"category": merchant_category, "idempotency_key": idempotency_key or ""},
        )

        # Debit user wallet
        WalletService.transfer(
            from_wallet=wallet,
            to_wallet=merchant_wallet,
            currency="INR",
            amount=amount_inr,
            category="PAYMENT",
            description=description or f"Payment to {merchant_name}",
            reference_id=reference_id,
            idempotency_key=f"PAY-{reference_id}",
            actor=user,
            metadata={"payment_id": str(payment.id)},
        )

        logger.info(f"[PAYMENT] INR ₹{amount_inr} to {merchant_name} settled immediately")
        return payment
