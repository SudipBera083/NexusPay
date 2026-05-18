"""Notification tasks — send real-time updates via Django Channels"""
import logging
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger("nexuspay")


@shared_task(name="apps.notifications.tasks.notify_transaction")
def notify_transaction(user_id: str, event_type: str, data: dict):
    """Push transaction notification to user WebSocket group"""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                "type": "transaction_notification",
                "data": {
                    "event_type": event_type,
                    **data,
                },
            },
        )
        logger.info(f"[NOTIFY] {event_type} sent to user {user_id}")
    except Exception as e:
        logger.error(f"[NOTIFY ERROR] {e}")


@shared_task(name="apps.notifications.tasks.notify_wallet_update")
def notify_wallet_update(user_id: str, inr_balance: str, usdt_balance: str):
    """Push updated wallet balance to user"""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                "type": "wallet_update",
                "data": {"inr_balance": inr_balance, "usdt_balance": usdt_balance},
            },
        )
    except Exception as e:
        logger.error(f"[WALLET NOTIFY ERROR] {e}")
