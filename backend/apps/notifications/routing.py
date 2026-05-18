"""WebSocket URL routing"""
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/wallet/", consumers.WalletConsumer.as_asgi()),
    path("ws/rates/", consumers.ExchangeRateConsumer.as_asgi()),
]
