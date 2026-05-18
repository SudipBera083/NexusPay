"""Transaction serializers"""
from decimal import Decimal
from rest_framework import serializers
from .models import ConversionHistory, PaymentTransaction


class ConversionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversionHistory
        fields = [
            "id", "from_currency", "to_currency", "from_amount", "to_amount",
            "rate", "gross_amount", "fee_amount", "spread_percent", "fee_percent",
            "status", "reference_id", "created_at",
        ]
        read_only_fields = fields


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = [
            "id", "merchant_name", "merchant_category", "amount_inr",
            "inr_from_balance", "usdt_converted", "inr_from_conversion",
            "conversion_rate", "description", "status", "reference_id", "created_at",
        ]
        read_only_fields = fields


class ConvertRequestSerializer(serializers.Serializer):
    from_currency = serializers.ChoiceField(choices=["INR", "USDT"])
    to_currency = serializers.ChoiceField(choices=["INR", "USDT"])
    amount = serializers.DecimalField(max_digits=15, decimal_places=8, min_value=Decimal("0.01"))

    def validate(self, attrs):
        if attrs["from_currency"] == attrs["to_currency"]:
            raise serializers.ValidationError("from_currency and to_currency must be different")
        return attrs


class PaymentRequestSerializer(serializers.Serializer):
    merchant_name = serializers.CharField(max_length=255)
    amount_inr = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal("1.00"))
    description = serializers.CharField(max_length=500, required=False, default="")
    merchant_category = serializers.CharField(max_length=100, required=False, default="General")
