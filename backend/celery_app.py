"""NexusPay Celery Application"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")

app = Celery("nexuspay")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# ─── Periodic Tasks ───────────────────────────────────────────────────────────

app.conf.beat_schedule = {
    "refresh-exchange-rates": {
        "task": "apps.exchange.tasks.refresh_exchange_rates",
        "schedule": 60.0,  # Every 60 seconds
    },
    "cleanup-expired-otps": {
        "task": "apps.authentication.tasks.cleanup_expired_otps",
        "schedule": crontab(minute="*/5"),
    },
    "generate-daily-audit-report": {
        "task": "apps.admin_panel.tasks.generate_daily_audit_report",
        "schedule": crontab(hour=0, minute=0),
    },
    "scan-fraud-signals": {
        "task": "apps.admin_panel.tasks.scan_fraud_signals",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
