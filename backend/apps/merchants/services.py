"""
Merchants Service Layer
========================
MerchantService: Onboarding, QR generation, verification, settlement
All financial operations route through WalletService double-entry engine.
"""
import uuid
import hmac
import hashlib
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from .models import Merchant, MerchantQRCode, MerchantStatus, QRCodeStatus
from apps.wallet.models import WalletType
from apps.wallet.services import WalletService
from core.events import EventDispatcher, DomainEventType

logger = logging.getLogger("nexuspay")


class MerchantService:

    @staticmethod
    @transaction.atomic
    def register_merchant(
        user,
        name: str,
        wallet_address: str,
        business_type: str = "General",
        category: str = "General",
        fee_structure: dict = None,
    ) -> Merchant:
        """
        Onboard a new merchant.
        Creates an internal settlement wallet for off-chain accounting.
        """
        if Merchant.objects.filter(wallet_address__iexact=wallet_address).exists():
            raise ValueError(f"Wallet address {wallet_address} is already registered to a merchant")

        # Create internal settlement wallet
        from apps.wallet.models import Wallet
        internal_wallet = Wallet.objects.create(
            type=WalletType.MERCHANT,
            label=f"Merchant: {name}",
        )

        merchant = Merchant.objects.create(
            user=user,
            name=name,
            business_type=business_type,
            category=category,
            wallet_address=wallet_address.lower(),
            internal_wallet=internal_wallet,
            fee_structure=fee_structure or {"settlement_fee_pct": 0.5, "min_fee_usdc": 0.01},
            status=MerchantStatus.ACTIVE,
            kyb_verified=False,
        )

        EventDispatcher.dispatch(
            event_type=DomainEventType.MERCHANT_REGISTERED,
            payload={"merchant_id": str(merchant.id), "name": name},
            user_id=str(user.id) if user else None,
        )

        logger.info(f"[MERCHANT] Registered: {name} | wallet={wallet_address}")
        return merchant

    @staticmethod
    def generate_qr(
        merchant: Merchant,
        amount_usdc: Decimal,
        description: str = "",
        expiry_seconds: int = None,
    ) -> MerchantQRCode:
        """
        Generate a time-limited, HMAC-signed QR payment code.
        Each call produces a unique nonce — prevents replay attacks.
        """
        if merchant.status != MerchantStatus.ACTIVE:
            raise ValueError(f"Merchant is not active: {merchant.status}")

        if amount_usdc <= Decimal("0"):
            raise ValueError("QR amount must be greater than zero")

        expiry = expiry_seconds or settings.QR_DEFAULT_EXPIRY_SECONDS
        expires_at = timezone.now() + timezone.timedelta(seconds=expiry)
        nonce = uuid.uuid4().hex  # One-time, cryptographically random

        qr = MerchantQRCode(
            merchant=merchant,
            merchant_wallet_address=merchant.wallet_address,
            amount_usdc=amount_usdc,
            description=description,
            nonce=nonce,
            expires_at=expires_at,
        )

        # Build canonical payload and sign it
        payload_str = qr.build_canonical_payload()
        secret = settings.QR_HMAC_SECRET.encode()
        signature = hmac.new(secret, payload_str.encode(), hashlib.sha256).hexdigest()

        qr.signed_payload = payload_str
        qr.hmac_signature = signature
        qr.save()

        logger.info(
            f"[QR] Generated: {qr.nonce[:8]}... | {amount_usdc} USDC | "
            f"merchant={merchant.name} | expires={expires_at.isoformat()}"
        )

        EventDispatcher.dispatch(
            event_type=DomainEventType.PAYMENT_QR_GENERATED,
            payload={
                "qr_id": str(qr.id),
                "merchant_id": str(merchant.id),
                "amount_usdc": str(amount_usdc),
                "nonce": nonce,
                "expires_at": expires_at.isoformat(),
            },
        )

        return qr

    @staticmethod
    def scan_qr(nonce: str, user) -> MerchantQRCode:
        """
        Process a QR scan event.
        Validates: exists, active, not expired, HMAC signature valid.
        """
        try:
            qr = MerchantQRCode.objects.select_related("merchant").get(nonce=nonce)
        except MerchantQRCode.DoesNotExist:
            raise ValueError("Invalid QR code")

        if qr.is_expired:
            if qr.status == QRCodeStatus.ACTIVE:
                qr.status = QRCodeStatus.EXPIRED
                qr.save(update_fields=["status"])
            raise ValueError("QR code has expired")

        if qr.status != QRCodeStatus.ACTIVE:
            raise ValueError(f"QR code is not active: {qr.status}")

        # Detect duplicate scan attempts (fraud signal)
        qr.scan_count += 1
        if qr.scan_count > 1:
            from apps.transactions.models import RiskFlag
            RiskFlag.objects.create(
                user=user,
                flag_type="DUPLICATE_QR_SCAN",
                severity="HIGH",
                details={
                    "qr_nonce": nonce,
                    "scan_count": qr.scan_count,
                    "merchant_id": str(qr.merchant_id),
                },
            )

        # Verify HMAC
        if not qr.verify_signature():
            raise ValueError("QR code signature verification failed — possible tampering")

        qr.created_for_user = user
        qr.transition_to(QRCodeStatus.SCANNED)
        qr.scan_count = qr.scan_count
        qr.save(update_fields=["created_for_user", "scan_count"])

        return qr

    @staticmethod
    def submit_transaction(nonce: str, tx_hash: str, wallet_address: str, user) -> MerchantQRCode:
        """
        Called when MetaMask broadcasts the blockchain transaction.
        Links the tx_hash to the QR code and advances the state machine.
        """
        try:
            qr = MerchantQRCode.objects.get(nonce=nonce)
        except MerchantQRCode.DoesNotExist:
            raise ValueError("QR code not found")

        if qr.created_for_user != user:
            raise PermissionError("QR code does not belong to this user")

        if qr.status not in [QRCodeStatus.SCANNED, QRCodeStatus.PENDING_SIGNATURE]:
            raise ValueError(f"Cannot submit transaction for QR in state: {qr.status}")

        qr.blockchain_tx_hash = tx_hash
        # Transitioning QR status is now handled by PaymentService below
        
        # We must link this to the PaymentTransaction!
        # Find the PaymentTransaction for this QR
        from apps.transactions.models import PaymentTransaction
        from apps.transactions.services import PaymentService
        
        try:
            payment = PaymentTransaction.objects.get(qr_code=qr, status="CREATED")
            PaymentService.submit_blockchain_signature(
                payment_id=str(payment.id),
                user=user,
                tx_hash=tx_hash,
                wallet_address=wallet_address
            )
        except PaymentTransaction.DoesNotExist:
            logger.warning(f"[MERCHANT] QR {nonce} submitted but no CREATED payment found.")

        # Register with blockchain indexer
        from apps.blockchain.tasks import poll_pending_transactions
        poll_pending_transactions.delay()

        logger.info(f"[MERCHANT] QR {nonce[:8]}... linked to tx {tx_hash[:12]}...")
        return qr

    @staticmethod
    def get_merchant_analytics(merchant: Merchant) -> dict:
        """Compute aggregated settlement analytics for a merchant"""
        from django.db.models import Sum, Count, Avg
        from apps.blockchain.models import SettlementEvent

        settlements = SettlementEvent.objects.filter(
            merchant_id=merchant.id,
            status="SETTLED",
        )

        agg = settlements.aggregate(
            total_usdc=Sum("usdc_amount"),
            total_fees=Sum("fee_amount"),
            total_net=Sum("net_amount"),
            count=Count("id"),
        )

        return {
            "merchant_id": str(merchant.id),
            "merchant_name": merchant.name,
            "total_settled_usdc": str(agg["total_usdc"] or 0),
            "total_fees_usdc": str(agg["total_fees"] or 0),
            "total_net_usdc": str(agg["total_net"] or 0),
            "settlement_count": agg["count"] or 0,
            "risk_score": merchant.risk_score,
        }
