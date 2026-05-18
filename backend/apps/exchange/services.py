"""Exchange rate service — CoinGecko integration with Redis caching"""
import logging
import httpx
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from .models import ExchangeRate

logger = logging.getLogger("nexuspay")

CACHE_KEY = "nexuspay:exchange_rate:USDT_INR"


class RateService:

    @staticmethod
    def fetch_from_coingecko() -> Decimal:
        """Fetch USDT/INR rate from CoinGecko public API"""
        url = f"{settings.COINGECKO_BASE_URL}/simple/price"
        params = {"ids": "tether", "vs_currencies": "inr"}
        headers = {}
        if settings.COINGECKO_API_KEY:
            headers["x-cg-pro-api-key"] = settings.COINGECKO_API_KEY

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                rate = Decimal(str(data["tether"]["inr"]))
                logger.info(f"[EXCHANGE] CoinGecko USDT/INR = {rate}")
                return rate
        except (httpx.HTTPError, KeyError, ValueError) as e:
            logger.error(f"[EXCHANGE] CoinGecko fetch failed: {e}")
            return None

    @staticmethod
    def get_current_rate(pair: str = "USDT_INR") -> ExchangeRate | None:
        """Get rate from cache or DB, fallback to CoinGecko"""
        cached = cache.get(CACHE_KEY)
        if cached:
            return cached

        # Try DB
        try:
            db_rate = ExchangeRate.objects.filter(currency_pair=pair).latest("fetched_at")
            cache.set(CACHE_KEY, db_rate, timeout=settings.EXCHANGE_RATE_CACHE_TTL)
            return db_rate
        except ExchangeRate.DoesNotExist:
            pass

        # Fetch from CoinGecko
        return RateService.refresh_rate(pair)

    @staticmethod
    def refresh_rate(pair: str = "USDT_INR") -> ExchangeRate | None:
        """Fetch fresh rate, store in DB and cache"""
        rate_value = RateService.fetch_from_coingecko()
        if rate_value is None:
            logger.warning("[EXCHANGE] Using fallback rate 84.50")
            rate_value = Decimal("84.50")  # Fallback

        spread = Decimal(str(settings.CONVERSION_SPREAD_PERCENT))
        exchange_rate = ExchangeRate.objects.create(
            currency_pair=pair,
            rate=rate_value,
            bid=rate_value * (1 - spread / 100),
            ask=rate_value * (1 + spread / 100),
            spread=spread,
        )

        cache.set(CACHE_KEY, exchange_rate, timeout=settings.EXCHANGE_RATE_CACHE_TTL)
        logger.info(f"[EXCHANGE] Refreshed {pair}: {rate_value}")
        return exchange_rate

    @staticmethod
    def calculate_conversion(
        from_currency: str,
        to_currency: str,
        amount: Decimal,
        rate_obj: ExchangeRate = None,
    ) -> dict:
        """Calculate conversion amounts including spread and fee"""
        if rate_obj is None:
            rate_obj = RateService.get_current_rate("USDT_INR")
            if rate_obj is None:
                from core.exceptions import ExchangeRateUnavailableError
                raise ExchangeRateUnavailableError()

        fee_percent = Decimal(str(settings.CONVERSION_FEE_PERCENT))

        if from_currency == "USDT" and to_currency == "INR":
            gross_inr = amount * rate_obj.sell_rate
            fee_inr = gross_inr * fee_percent / 100
            net_inr = gross_inr - fee_inr
            return {
                "from_amount": amount,
                "to_amount": net_inr.quantize(Decimal("0.01")),
                "rate": rate_obj.sell_rate,
                "gross_amount": gross_inr,
                "fee_amount": fee_inr.quantize(Decimal("0.01")),
                "spread_percent": float(rate_obj.spread),
                "fee_percent": float(fee_percent),
                "rate_obj_id": str(rate_obj.id),
            }
        elif from_currency == "INR" and to_currency == "USDT":
            fee_inr = amount * fee_percent / 100
            net_inr = amount - fee_inr
            usdt_amount = net_inr / rate_obj.buy_rate
            return {
                "from_amount": amount,
                "to_amount": usdt_amount.quantize(Decimal("0.00000001")),
                "rate": rate_obj.buy_rate,
                "gross_amount": amount / rate_obj.buy_rate,
                "fee_amount": fee_inr.quantize(Decimal("0.01")),
                "spread_percent": float(rate_obj.spread),
                "fee_percent": float(fee_percent),
                "rate_obj_id": str(rate_obj.id),
            }
        else:
            from core.exceptions import InvalidCurrencyError
            raise InvalidCurrencyError(f"Unsupported pair: {from_currency}→{to_currency}")
