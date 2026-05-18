"""Exchange views"""
from decimal import Decimal
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework import serializers
from drf_spectacular.utils import extend_schema

from core.response import APIResponse
from core.pagination import StandardResultsPagination
from .models import ExchangeRate
from .services import RateService


class ExchangeRateSerializer(serializers.ModelSerializer):
    buy_rate = serializers.DecimalField(max_digits=20, decimal_places=8, read_only=True)
    sell_rate = serializers.DecimalField(max_digits=20, decimal_places=8, read_only=True)

    class Meta:
        model = ExchangeRate
        fields = ["id", "currency_pair", "rate", "buy_rate", "sell_rate", "bid", "ask",
                  "spread", "source", "is_live", "fetched_at"]


class ConversionQuoteSerializer(serializers.Serializer):
    from_currency = serializers.ChoiceField(choices=["INR", "USDT"])
    to_currency = serializers.ChoiceField(choices=["INR", "USDT"])
    amount = serializers.DecimalField(max_digits=15, decimal_places=8, min_value=Decimal("0.01"))

    def validate(self, attrs):
        if attrs["from_currency"] == attrs["to_currency"]:
            raise serializers.ValidationError("from_currency and to_currency must be different")
        return attrs


class CurrentRateView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["Exchange"], summary="Get current USDT/INR rate")
    def get(self, request):
        rate = RateService.get_current_rate("USDT_INR")
        if not rate:
            rate = RateService.refresh_rate("USDT_INR")
        return APIResponse.success(data=ExchangeRateSerializer(rate).data)


class ConversionQuoteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Exchange"], request=ConversionQuoteSerializer, summary="Get conversion quote")
    def post(self, request):
        serializer = ConversionQuoteSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(serializer.errors)

        data = serializer.validated_data
        quote = RateService.calculate_conversion(
            from_currency=data["from_currency"],
            to_currency=data["to_currency"],
            amount=data["amount"],
        )
        return APIResponse.success(data=quote, message="Conversion quote calculated")


class RateHistoryView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["Exchange"], summary="Get exchange rate history")
    def get(self, request):
        qs = ExchangeRate.objects.filter(currency_pair="USDT_INR").order_by("-fetched_at")[:100]
        return APIResponse.success(data=ExchangeRateSerializer(qs, many=True).data)
