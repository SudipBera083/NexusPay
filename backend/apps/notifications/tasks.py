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


@shared_task(name="apps.notifications.tasks.process_domain_event")
def process_domain_event(event_dict: dict):
    """
    Background worker for processing DomainEvents.
    Routes events to specific side-effect handlers (e.g., push notifications, audit logs).
    """
    event_type = event_dict.get("event_type")
    user_id = event_dict.get("user_id")
    payload = event_dict.get("payload", {})
    
    logger.info(f"[EVENT WORKER] Processing {event_type}")

    # Push certain events directly to the user's WebSocket
    push_events = [
        "PaymentQRGenerated", "BlockchainSubmitted", "BlockchainConfirmed",
        "SettlementCompleted", "DepositCompleted", "ConversionExecuted",
        "PaymentFailed", "FraudDetected",
    ]
    
    if user_id and event_type in push_events:
        notify_transaction.delay(user_id, event_type, payload)
        
    # Push system/critical events to admin groups
    admin_events = [
        "FraudDetected", "ReconciliationFailed", "TreasuryImbalanceDetected",
        "JournalImbalanceDetected", "RiskFlagCreated",
    ]
    
    if event_type in admin_events:
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "admin_notifications",
                {
                    "type": "admin_notification",
                    "data": {
                        "event_type": event_type,
                        **payload,
                    },
                },
            )
        except Exception as e:
            logger.error(f"[ADMIN NOTIFY ERROR] {e}")

