"""Async tasks for authentication"""
import logging
from celery import shared_task

logger = logging.getLogger("nexuspay")


@shared_task(name="apps.authentication.tasks.send_otp_task")
def send_otp_task(email: str, otp_code: str):
    """Send OTP via SMS/email — simulated in this demo"""
    logger.info(f"[OTP TASK] Would send OTP {otp_code} to {email}")
    # TODO: Integrate Twilio/SendGrid for production
    return {"email": email, "status": "simulated"}


@shared_task(name="apps.authentication.tasks.cleanup_expired_otps")
def cleanup_expired_otps():
    """Clear OTPs older than 5 minutes"""
    from django.utils import timezone
    from datetime import timedelta
    from .models import User

    cutoff = timezone.now() - timedelta(minutes=5)
    expired = User.objects.filter(otp_created_at__lt=cutoff).exclude(otp_secret=None)
    count = expired.update(otp_secret=None, otp_created_at=None)
    logger.info(f"[OTP CLEANUP] Cleared {count} expired OTPs")
    return count
