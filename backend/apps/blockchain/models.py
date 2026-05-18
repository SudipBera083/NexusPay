"""
Blockchain App — Models
========================
BlockchainTransaction: On-chain transaction lifecycle tracking
SettlementEvent: Links blockchain confirmation to internal settlement
"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings


class BlockchainTxStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Submitted to Mempool"
    MEMPOOL_PENDING = "MEMPOOL_PENDING", "Pending in Mempool"
    CONFIRMING = "CONFIRMING", "Collecting Confirmations"
    CONFIRMED = "CONFIRMED", "Confirmed"
    FAILED = "FAILED", "Failed / Reverted"
    DROPPED = "DROPPED", "Dropped from Mempool"
    REORGED = "REORGED", "Block Reorg Detected"


class BlockchainTransaction(models.Model):
    """
    Represents a single on-chain transaction tracked by the indexer.
    The backend NEVER creates transactions — it only records + monitors them.
    Source of truth: the blockchain itself.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # On-chain identity
    tx_hash = models.CharField(max_length=66, unique=True, db_index=True)
    from_address = models.CharField(max_length=42, db_index=True)
    to_address = models.CharField(max_length=42, db_index=True)
    token_contract = models.CharField(max_length=42)
    token_symbol = models.CharField(max_length=20, default="USDC")

    # Amounts (raw wei and human-readable)
    amount_raw = models.CharField(max_length=78)  # wei as string to avoid precision loss
    amount_human = models.DecimalField(max_digits=24, decimal_places=8)

    # Network
    chain_id = models.IntegerField(default=80002)  # Polygon Amoy
    block_number = models.BigIntegerField(null=True, blank=True)
    confirmations = models.IntegerField(default=0)
    required_confirmations = models.IntegerField(default=3)

    # Status
    status = models.CharField(
        max_length=20,
        choices=BlockchainTxStatus.choices,
        default=BlockchainTxStatus.SUBMITTED,
        db_index=True,
    )

    # Provider tracking
    submitted_via_provider = models.CharField(max_length=50, blank=True)
    gas_used = models.BigIntegerField(null=True, blank=True)
    gas_price_gwei = models.DecimalField(max_digits=20, decimal_places=9, null=True, blank=True)

    # Internal links
    payment_intent_id = models.UUIDField(null=True, blank=True, db_index=True)
    qr_code_nonce = models.CharField(max_length=100, blank=True, db_index=True)

    # Decoded log data (from ERC20 Transfer event)
    decoded_log = models.JSONField(default=dict, blank=True)

    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "blockchain_transactions"
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["status", "-submitted_at"]),
            models.Index(fields=["from_address", "-submitted_at"]),
            models.Index(fields=["to_address", "-submitted_at"]),
        ]

    def __str__(self):
        return f"{self.tx_hash[:12]}... [{self.status}] {self.amount_human} {self.token_symbol}"

    @property
    def is_finalized(self):
        return self.status in [
            BlockchainTxStatus.CONFIRMED,
            BlockchainTxStatus.FAILED,
            BlockchainTxStatus.DROPPED,
            BlockchainTxStatus.REORGED,
        ]

    @property
    def confirmation_progress(self) -> float:
        """Progress 0.0 → 1.0"""
        if self.required_confirmations == 0:
            return 1.0
        return min(self.confirmations / self.required_confirmations, 1.0)


class SettlementEvent(models.Model):
    """
    Records the internal accounting settlement triggered by a blockchain confirmation.
    Links: BlockchainTransaction → JournalEntry → Merchant payout
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    blockchain_tx = models.OneToOneField(
        BlockchainTransaction,
        on_delete=models.PROTECT,
        related_name="settlement",
    )

    # Who / what was settled
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="settlement_events",
    )
    merchant_id = models.UUIDField(null=True, blank=True)

    # Settlement amounts
    usdc_amount = models.DecimalField(max_digits=24, decimal_places=8)
    fee_amount = models.DecimalField(max_digits=24, decimal_places=8, default=Decimal("0"))
    net_amount = models.DecimalField(max_digits=24, decimal_places=8)

    # Internal accounting link
    journal_entry_id = models.UUIDField(null=True, blank=True)

    class SettlementStatus(models.TextChoices):
        PROCESSING = "PROCESSING", "Processing"
        SETTLED = "SETTLED", "Settled"
        FAILED = "FAILED", "Failed"
        DISPUTED = "DISPUTED", "Disputed"

    status = models.CharField(
        max_length=20,
        choices=SettlementStatus.choices,
        default=SettlementStatus.PROCESSING,
    )

    metadata = models.JSONField(default=dict, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "settlement_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Settlement {self.id} [{self.status}] {self.usdc_amount} USDC"
