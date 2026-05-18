"""Admin panel Celery tasks — daily audit report + fraud signal scanner"""
import logging
from decimal import Decimal
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger("nexuspay")


@shared_task(name="apps.admin_panel.tasks.generate_daily_audit_report")
def generate_daily_audit_report():
    """Generate daily summary of platform activity"""
    from apps.wallet.models import WalletTransaction, AuditLog
    from apps.transactions.models import PaymentTransaction, ConversionHistory
    from django.db.models import Sum

    yesterday = timezone.now().replace(hour=0, minute=0, second=0) - timedelta(days=1)
    today = timezone.now().replace(hour=0, minute=0, second=0)

    payments = PaymentTransaction.objects.filter(created_at__range=(yesterday, today))
    conversions = ConversionHistory.objects.filter(created_at__range=(yesterday, today))

    report = {
        "date": yesterday.date().isoformat(),
        "payments": {
            "count": payments.count(),
            "volume_inr": str(payments.aggregate(total=Sum("amount_inr"))["total"] or 0),
        },
        "conversions": {
            "count": conversions.count(),
            "fees": str(conversions.aggregate(total=Sum("fee_amount"))["total"] or 0),
        },
    }
    logger.info(f"[AUDIT REPORT] {report}")
    return report


@shared_task(name="apps.admin_panel.tasks.scan_fraud_signals")
def scan_fraud_signals():
    """
    Periodic fraud signal scanner.
    Detects and persists risk flags for:
    - LARGE_TRANSACTION: Single tx >= ₹50,000 or 500 USDT
    - HIGH_FREQUENCY: More than 10 transactions in 10 minutes
    - RAPID_LARGE_SPENDING: Spending > ₹1,00,000 within 1 hour
    """
    from apps.wallet.models import WalletTransaction
    from apps.transactions.models import RiskFlag
    from django.db.models import Count, Sum
    from django.contrib.auth import get_user_model

    User = get_user_model()
    now = timezone.now()
    window_10m = now - timedelta(minutes=10)
    window_1h = now - timedelta(hours=1)
    flagged_count = 0

    # ── Rule 1: LARGE_TRANSACTION ─────────────────────────────
    large_txs = WalletTransaction.objects.filter(
        created_at__gte=window_1h,
        amount__gte=Decimal("50000"),
        currency="INR",
    ).select_related("wallet__user")

    large_txs_usdt = WalletTransaction.objects.filter(
        created_at__gte=window_1h,
        amount__gte=Decimal("500"),
        currency="USDT",
    ).select_related("wallet__user")

    for tx in list(large_txs) + list(large_txs_usdt):
        # Avoid duplicate flags for same tx
        if not RiskFlag.objects.filter(transaction=tx, flag_type="LARGE_TRANSACTION").exists():
            RiskFlag.objects.create(
                user=tx.wallet.user,
                wallet=tx.wallet,
                transaction=tx,
                flag_type="LARGE_TRANSACTION",
                severity="HIGH" if float(tx.amount) >= 100000 else "MEDIUM",
                details={
                    "amount": str(tx.amount),
                    "currency": tx.currency,
                    "category": tx.category,
                    "reference_id": tx.reference_id,
                },
            )
            flagged_count += 1

    # ── Rule 2: HIGH_FREQUENCY ────────────────────────────────
    freq_data = (
        WalletTransaction.objects.filter(created_at__gte=window_10m)
        .values("wallet_id")
        .annotate(count=Count("id"))
        .filter(count__gte=10)
    )

    for row in freq_data:
        if not RiskFlag.objects.filter(
            wallet_id=row["wallet_id"],
            flag_type="HIGH_FREQUENCY",
            created_at__gte=window_10m,
        ).exists():
            from apps.wallet.models import Wallet
            try:
                wallet = Wallet.objects.select_related("user").get(pk=row["wallet_id"])
            except Wallet.DoesNotExist:
                continue
            RiskFlag.objects.create(
                user=wallet.user,
                wallet=wallet,
                flag_type="HIGH_FREQUENCY",
                severity="HIGH",
                details={
                    "transaction_count": row["count"],
                    "window_minutes": 10,
                },
            )
            flagged_count += 1

    # ── Rule 3: RAPID_LARGE_SPENDING ─────────────────────────
    spending_data = (
        WalletTransaction.objects.filter(
            created_at__gte=window_1h,
            transaction_type="DEBIT",
            currency="INR",
        )
        .values("wallet_id")
        .annotate(total=Sum("amount"))
        .filter(total__gte=Decimal("100000"))
    )

    for row in spending_data:
        if not RiskFlag.objects.filter(
            wallet_id=row["wallet_id"],
            flag_type="RAPID_LARGE_SPENDING",
            created_at__gte=window_1h,
        ).exists():
            from apps.wallet.models import Wallet
            try:
                wallet = Wallet.objects.select_related("user").get(pk=row["wallet_id"])
            except Wallet.DoesNotExist:
                continue
            RiskFlag.objects.create(
                user=wallet.user,
                wallet=wallet,
                flag_type="RAPID_LARGE_SPENDING",
                severity="CRITICAL",
                details={
                    "total_spent_inr": str(row["total"]),
                    "window_hours": 1,
                },
            )
            flagged_count += 1

    logger.info(f"[FRAUD SCAN] Completed. {flagged_count} new risk flags created.")
    return {"flags_created": flagged_count}
