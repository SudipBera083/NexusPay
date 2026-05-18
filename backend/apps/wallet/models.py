"""Wallet models — Wallet, WalletTransaction, AuditLog"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings


class WalletType(models.TextChoices):
    USER = "USER", "User Wallet"
    MERCHANT = "MERCHANT", "Merchant Wallet"
    TREASURY_EXTERNAL = "TREASURY_EXTERNAL", "External Banking System"
    TREASURY_EXTERNAL_UPI = "TREASURY_EXTERNAL_UPI", "UPI On-Ramp Treasury"
    TREASURY_USDC_RESERVE = "TREASURY_USDC_RESERVE", "USDC Reserve Treasury"
    TREASURY_RESERVE_INR = "TREASURY_RESERVE_INR", "INR Reserve Treasury"
    TREASURY_RESERVE_USDT = "TREASURY_RESERVE_USDT", "USDT Reserve Treasury"
    TREASURY_SETTLEMENT = "TREASURY_SETTLEMENT", "Merchant Settlement Pool"
    TREASURY_FEES = "TREASURY_FEES", "Fee Collection Treasury"
    TREASURY_BLOCKCHAIN_GAS = "TREASURY_BLOCKCHAIN_GAS", "Gas Reserve Treasury"
    TREASURY_RISK_BUFFER = "TREASURY_RISK_BUFFER", "Risk Buffer Treasury"


class CurrencyChoice(models.TextChoices):
    INR = "INR", "Indian Rupee"
    USDT = "USDT", "Tether USD"
    USDC = "USDC", "USD Coin"


class TransactionType(models.TextChoices):
    CREDIT = "CREDIT", "Credit"
    DEBIT = "DEBIT", "Debit"


class TransactionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    REVERSED = "REVERSED", "Reversed"


class TransactionCategory(models.TextChoices):
    DEPOSIT = "DEPOSIT", "Deposit"
    WITHDRAWAL = "WITHDRAWAL", "Withdrawal"
    CONVERSION = "CONVERSION", "Conversion"
    PAYMENT = "PAYMENT", "Payment"
    REFUND = "REFUND", "Refund"
    FEE = "FEE", "Fee"
    REVERSAL = "REVERSAL", "Reversal"


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=30, choices=WalletType.choices, default=WalletType.USER)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
        null=True,
        blank=True,
    )
    label = models.CharField(max_length=255, blank=True, default="", help_text="Display name for treasury/merchant wallets")
    inr_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    usdt_balance = models.DecimalField(max_digits=15, decimal_places=8, default=Decimal("0.00000000"))
    usdc_balance = models.DecimalField(max_digits=24, decimal_places=8, default=Decimal("0.00000000"))
    web3_address = models.CharField(max_length=42, null=True, blank=True, unique=True, help_text="Linked external EVM wallet address")
    is_active = models.BooleanField(default=True)
    is_locked = models.BooleanField(default=False)
    lock_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wallets"
        verbose_name = "Wallet"

    def __str__(self):
        if self.type == WalletType.USER and self.user:
            return f"Wallet({self.user.email}) INR={self.inr_balance} USDT={self.usdt_balance}"
        return f"{self.get_type_display()} INR={self.inr_balance} USDT={self.usdt_balance}"

    def get_balance(self, currency: str) -> Decimal:
        if currency in [CurrencyChoice.INR, "INR"]:
            return self.inr_balance
        elif currency in [CurrencyChoice.USDC, "USDC"]:
            return self.usdc_balance
        elif currency in [CurrencyChoice.USDT, "USDT"]:
            return self.usdt_balance
        raise ValueError(f"Unknown currency: {currency}")

    def set_balance(self, currency: str, value: Decimal):
        if currency in [CurrencyChoice.INR, "INR"]:
            self.inr_balance = value
        elif currency in [CurrencyChoice.USDC, "USDC"]:
            self.usdc_balance = value
        elif currency in [CurrencyChoice.USDT, "USDT"]:
            self.usdt_balance = value
        else:
            raise ValueError(f"Unknown currency: {currency}")

    def balance_field(self, currency: str) -> str:
        if currency in [CurrencyChoice.INR, "INR"]:
            return "inr_balance"
        elif currency in [CurrencyChoice.USDC, "USDC"]:
            return "usdc_balance"
        return "usdt_balance"


class JournalEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "journal_entries"
        verbose_name = "Journal Entry"

    def __str__(self):
        return f"Journal {self.id}"


class WalletTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.PROTECT, related_name="transactions", null=True)
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="transactions")
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    currency = models.CharField(max_length=10, choices=CurrencyChoice.choices)
    category = models.CharField(max_length=20, choices=TransactionCategory.choices, default=TransactionCategory.DEPOSIT)
    amount = models.DecimalField(max_digits=15, decimal_places=8)
    balance_before = models.DecimalField(max_digits=15, decimal_places=8)
    balance_after = models.DecimalField(max_digits=15, decimal_places=8)
    description = models.TextField(blank=True)
    reference_id = models.CharField(max_length=100, blank=True, db_index=True)
    related_transaction = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="related"
    )
    status = models.CharField(max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.COMPLETED)
    idempotency_key = models.CharField(max_length=100, unique=True, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wallet_transactions"
        verbose_name = "Wallet Transaction"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "currency", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["reference_id"]),
        ]

    def __str__(self):
        return f"{self.transaction_type} {self.amount} {self.currency} [{self.status}]"


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=100, blank=True)
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.timestamp}] {self.action} on {self.resource_type}"

    @classmethod
    def log(cls, actor, action: str, resource_type: str, resource_id: str = "",
            before=None, after=None, request=None):
        ip = None
        ua = ""
        if request:
            ip = request.META.get("REMOTE_ADDR")
            ua = request.META.get("HTTP_USER_AGENT", "")[:500]
        cls.objects.create(
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            before_state=before,
            after_state=after,
            ip_address=ip,
            user_agent=ua,
        )
