"""Exchange rate models"""
import uuid
from decimal import Decimal
from django.db import models


class ExchangeRate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    currency_pair = models.CharField(max_length=20, db_index=True)  # e.g., USDT_INR
    rate = models.DecimalField(max_digits=20, decimal_places=8)
    bid = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    ask = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    spread = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal("0.5"))
    source = models.CharField(max_length=50, default="CoinGecko")
    is_live = models.BooleanField(default=True)
    fetched_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "exchange_rates"
        ordering = ["-fetched_at"]
        indexes = [models.Index(fields=["currency_pair", "-fetched_at"])]

    def __str__(self):
        return f"{self.currency_pair}: {self.rate} @ {self.fetched_at}"

    @property
    def buy_rate(self) -> Decimal:
        """Rate at which users buy USDT (with spread)"""
        spread_factor = Decimal(str(self.spread)) / 100
        return self.rate * (1 + spread_factor)

    @property
    def sell_rate(self) -> Decimal:
        """Rate at which users sell USDT (with spread subtracted)"""
        spread_factor = Decimal(str(self.spread)) / 100
        return self.rate * (1 - spread_factor)
