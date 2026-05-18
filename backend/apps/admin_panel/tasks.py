"""Admin panel Celery tasks"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("nexuspay")


@shared_task(name="apps.admin_panel.tasks.generate_daily_audit_report")
def generate_daily_audit_report():
    """Generate daily summary of platform activity"""
    from apps.wallet.models import WalletTransaction, AuditLog
    from apps.transactions.models import PaymentTransaction, ConversionHistory
    from django.db.models import Sum, Count

    yesterday = timezone.now().replace(hour=0, minute=0, second=0) - timezone.timedelta(days=1)
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
