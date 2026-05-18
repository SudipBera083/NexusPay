"""Celery tasks for exchange rate management"""
import logging
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger("nexuspay")


@shared_task(
    name="apps.exchange.tasks.refresh_exchange_rates",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def refresh_exchange_rates(self):
    """Fetch fresh exchange rates and broadcast via WebSocket"""
    try:
        from .services import RateService
        rate_obj = RateService.refresh_rate("USDT_INR")

        if rate_obj:
            # Broadcast to all connected WebSocket clients
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "exchange_rates",
                {
                    "type": "rate_update",
                    "data": {
                        "pair": rate_obj.currency_pair,
                        "rate": str(rate_obj.rate),
                        "buy_rate": str(rate_obj.buy_rate),
                        "sell_rate": str(rate_obj.sell_rate),
                        "spread": str(rate_obj.spread),
                        "fetched_at": rate_obj.fetched_at.isoformat(),
                    },
                },
            )
            logger.info(f"[EXCHANGE TASK] Refreshed and broadcast rate: {rate_obj.rate}")
            return {"rate": str(rate_obj.rate), "status": "ok"}
    except Exception as exc:
        logger.error(f"[EXCHANGE TASK] Failed: {exc}")
        raise self.retry(exc=exc)
