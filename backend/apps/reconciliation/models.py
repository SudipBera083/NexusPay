"""
Reconciliation Engine — Models
================================
ReconciliationReport: Records the result of each reconciliation run.
Discrepancies are stored as structured JSON for audit trails.
"""
import uuid
from django.db import models


class ReportType(models.TextChoices):
    WALLET_BALANCE = "WALLET_BALANCE", "Wallet Balance Integrity"
    JOURNAL_BALANCE = "JOURNAL_BALANCE", "Journal Entry Net-Zero"
    TREASURY_INTEGRITY = "TREASURY_INTEGRITY", "Treasury Total Integrity"
    BLOCKCHAIN_SETTLEMENT = "BLOCKCHAIN_SETTLEMENT", "Blockchain Settlement Verification"
    ORPHAN_TRANSACTIONS = "ORPHAN_TRANSACTIONS", "Orphan Transaction Detection"


class ReportStatus(models.TextChoices):
    PASS = "PASS", "Pass — No Discrepancies"
    FAIL = "FAIL", "Fail — Discrepancies Found"
    ERROR = "ERROR", "Error — Reconciliation Failed"


class ReconciliationReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(max_length=30, choices=ReportType.choices, db_index=True)
    status = models.CharField(max_length=10, choices=ReportStatus.choices, db_index=True)

    # Summary counts
    records_checked = models.IntegerField(default=0)
    discrepancy_count = models.IntegerField(default=0)

    # Structured discrepancy data
    discrepancies = models.JSONField(default=list, blank=True)
    summary = models.TextField(blank=True)

    run_at = models.DateTimeField(auto_now_add=True, db_index=True)
    duration_ms = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "reconciliation_reports"
        ordering = ["-run_at"]
        indexes = [
            models.Index(fields=["report_type", "status", "-run_at"]),
        ]

    def __str__(self):
        return f"[{self.status}] {self.report_type} @ {self.run_at}"
