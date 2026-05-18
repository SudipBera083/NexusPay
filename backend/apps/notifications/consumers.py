"""Django Channels WebSocket consumers for NexusPay"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger("nexuspay")


class WalletConsumer(AsyncWebsocketConsumer):
    """Per-user WebSocket: live balance updates + transaction notifications"""

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.user_id = str(user.id)
        self.user_group = f"user_{self.user_id}"

        # Join user-specific group
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()
        logger.info(f"[WS] User {user.email} connected")

        # Send current balance on connect
        balance = await self.get_wallet_balance(user)
        await self.send(text_data=json.dumps({"type": "wallet_balance", "data": balance}))

    async def disconnect(self, close_code):
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
            logger.info(f"[WS] User {self.user_id} disconnected (code={close_code})")

    async def receive(self, text_data):
        """Handle incoming messages (e.g., ping)"""
        try:
            data = json.loads(text_data)
            if data.get("type") == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        except json.JSONDecodeError:
            pass

    async def wallet_update(self, event):
        """Receive wallet update from channel layer → send to WebSocket client"""
        await self.send(text_data=json.dumps({"type": "wallet_update", "data": event["data"]}))

    async def transaction_notification(self, event):
        """Receive transaction notification → send to client"""
        await self.send(text_data=json.dumps({"type": "transaction_notification", "data": event["data"]}))

    async def rate_update(self, event):
        """Rate update broadcast"""
        await self.send(text_data=json.dumps({"type": "rate_update", "data": event["data"]}))

    @database_sync_to_async
    def get_wallet_balance(self, user):
        from apps.wallet.models import Wallet
        try:
            wallet = Wallet.objects.get(user=user)
            return {
                "inr_balance": str(wallet.inr_balance),
                "usdt_balance": str(wallet.usdt_balance),
                "is_active": wallet.is_active,
            }
        except Wallet.DoesNotExist:
            return {"inr_balance": "0.00", "usdt_balance": "0.00000000"}


class ExchangeRateConsumer(AsyncWebsocketConsumer):
    """Public WebSocket: live exchange rate broadcast"""

    async def connect(self):
        self.group_name = "exchange_rates"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info("[WS] Exchange rate subscriber connected")

        # Send latest rate on connect
        rate = await self.get_latest_rate()
        if rate:
            await self.send(text_data=json.dumps({"type": "rate_update", "data": rate}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def rate_update(self, event):
        await self.send(text_data=json.dumps({"type": "rate_update", "data": event["data"]}))

    @database_sync_to_async
    def get_latest_rate(self):
        from apps.exchange.models import ExchangeRate
        try:
            r = ExchangeRate.objects.latest("fetched_at")
            return {
                "pair": r.currency_pair,
                "rate": str(r.rate),
                "buy_rate": str(r.buy_rate),
                "sell_rate": str(r.sell_rate),
                "fetched_at": r.fetched_at.isoformat(),
            }
        except ExchangeRate.DoesNotExist:
            return None
