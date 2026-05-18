"""Transaction models — ConversionHistory + PaymentTransaction"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from apps.wallet.models import Wallet, WalletType


class ConversionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class ConversionHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversions")
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="conversions")
    from_currency = models.CharField(max_length=10)
    to_currency = models.CharField(max_length=10)
    from_amount = models.DecimalField(max_digits=15, decimal_places=8)
    to_amount = models.DecimalField(max_digits=15, decimal_places=8)
    rate = models.DecimalField(max_digits=20, decimal_places=8)
    gross_amount = models.DecimalField(max_digits=15, decimal_places=8)
    fee_amount = models.DecimalField(max_digits=15, decimal_places=8)
    spread_percent = models.DecimalField(max_digits=5, decimal_places=4)
    fee_percent = models.DecimalField(max_digits=5, decimal_places=4)
    status = models.CharField(max_length=20, choices=ConversionStatus.choices, default=ConversionStatus.PENDING)
    reference_id = models.CharField(max_length=100, unique=True, db_index=True)
    debit_tx = models.UUIDField(null=True, blank=True)   # WalletTransaction ID
    credit_tx = models.UUIDField(null=True, blank=True)
    fee_tx = models.UUIDField(null=True, blank=True)
    exchange_rate_id = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conversion_history"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.from_amount} {self.from_currency} → {self.to_amount} {self.to_currency}"


class PaymentStatus(models.TextChoices):
    CREATED = "CREATED", "Payment Created"
    SUBMITTED = "SUBMITTED", "Submitted to Blockchain"
    CONFIRMED = "CONFIRMED", "Confirmed & Settled"
    FAILED = "FAILED", "Failed"


class PaymentTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments")
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="payments")
    merchant = models.ForeignKey("merchants.Merchant", on_delete=models.PROTECT, related_name="payments")
    amount_inr = models.DecimalField(max_digits=15, decimal_places=2)
    inr_from_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    usdt_converted = models.DecimalField(max_digits=15, decimal_places=8, default=Decimal("0.00000000"))
    inr_from_conversion = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    conversion_rate = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.CREATED,
        db_index=True,
    )
    reference_id = models.CharField(max_length=100, unique=True, db_index=True)
    related_conversion = models.ForeignKey(
        ConversionHistory, null=True, blank=True, on_delete=models.SET_NULL, related_name="payments"
    )
    wallet_tx = models.UUIDField(null=True, blank=True)
    qr_code = models.ForeignKey(
        "merchants.MerchantQRCode", null=True, blank=True, on_delete=models.SET_NULL, related_name="payment"
    )
    blockchain_tx = models.ForeignKey(
        "blockchain.BlockchainTransaction", null=True, blank=True, on_delete=models.SET_NULL, related_name="payment"
    )
    blockchain_tx_hash = models.CharField(max_length=66, unique=True, null=True, blank=True)
    settlement_event = models.ForeignKey(
        "blockchain.SettlementEvent", null=True, blank=True, on_delete=models.SET_NULL, related_name="payment"
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payment_transactions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment ₹{self.amount_inr} to {self.merchant.name} [{self.status}]"

    def transition_to(self, new_status: str) -> bool:
        """Enforces valid state transitions."""
        valid_transitions = {
            PaymentStatus.CREATED: [PaymentStatus.SUBMITTED, PaymentStatus.FAILED],
            PaymentStatus.SUBMITTED: [PaymentStatus.CONFIRMED, PaymentStatus.FAILED],
            PaymentStatus.CONFIRMED: [],
            PaymentStatus.FAILED: [],
        }

        allowed = valid_transitions.get(self.status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Invalid Payment transition: {self.status} → {new_status}. "
                f"Allowed: {[s for s in allowed]}"
            )

        self.status = new_status
        self.save(update_fields=["status", "updated_at"])
        
        # Dispatch event on critical transitions
        from core.events import EventDispatcher, DomainEventType
        event_map = {
            PaymentStatus.CREATED: DomainEventType.PAYMENT_CREATED,
            PaymentStatus.SUBMITTED: DomainEventType.BLOCKCHAIN_SUBMITTED,
            PaymentStatus.CONFIRMED: DomainEventType.BLOCKCHAIN_CONFIRMED,
            PaymentStatus.FAILED: DomainEventType.PAYMENT_FAILED,
        }
        
        if new_status in event_map:
            EventDispatcher.dispatch(
                event_type=event_map[new_status],
                payload={"payment_id": str(self.id), "status": new_status},
                user_id=str(self.user_id),
            )
            
        return True


class RiskFlagSeverity(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class RiskFlag(models.Model):
    """Persisted fraud/risk signals for compliance and admin review"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="risk_flags"
    )
    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name="risk_flags", null=True, blank=True
    )
    transaction = models.ForeignKey(
        "wallet.WalletTransaction",
        null=True, blank=True, on_delete=models.SET_NULL, related_name="risk_flags"
    )
    flag_type = models.CharField(max_length=50)  # e.g. LARGE_TRANSACTION, RAPID_SPENDING, HIGH_FREQUENCY
    severity = models.CharField(max_length=20, choices=RiskFlagSeverity.choices, default=RiskFlagSeverity.MEDIUM)
    details = models.JSONField(default=dict)
    is_reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_flags"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "risk_flags"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["severity", "is_reviewed"]),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.flag_type} — {self.user_id}"
