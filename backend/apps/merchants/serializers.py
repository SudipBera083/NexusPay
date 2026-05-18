"""Merchant serializers"""
from decimal import Decimal
from rest_framework import serializers
from .models import Merchant, MerchantQRCode


class MerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = [
            "id", "name", "business_type", "category", "wallet_address",
            "fee_structure", "risk_score", "kyb_verified", "status",
            "total_settlements_usdc", "total_payment_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "risk_score", "total_settlements_usdc",
                            "total_payment_count", "created_at", "updated_at"]


class RegisterMerchantSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    wallet_address = serializers.CharField(max_length=42)
    business_type = serializers.CharField(max_length=100, default="General")
    category = serializers.CharField(max_length=100, default="General")

    def validate_wallet_address(self, value):
        if not value.startswith("0x") or len(value) != 42:
            raise serializers.ValidationError("Must be a valid EVM address (0x... 42 chars)")
        return value.lower()


class GenerateQRSerializer(serializers.Serializer):
    amount_usdc = serializers.DecimalField(max_digits=24, decimal_places=8, min_value=Decimal("0.01"))
    description = serializers.CharField(max_length=255, default="", allow_blank=True)
    expiry_seconds = serializers.IntegerField(min_value=60, max_value=3600, default=300)


class MerchantQRCodeSerializer(serializers.ModelSerializer):
    is_active = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    merchant_name = serializers.ReadOnlyField(source="merchant.name")
    merchant_wallet_address = serializers.ReadOnlyField()

    class Meta:
        model = MerchantQRCode
        fields = [
            "id", "merchant_name", "merchant_wallet_address",
            "amount_usdc", "currency", "description",
            "nonce", "signed_payload", "hmac_signature",
            "status", "expires_at", "is_active", "is_expired",
            "blockchain_tx_hash", "scan_count", "created_at",
        ]
        read_only_fields = fields


class ScanQRSerializer(serializers.Serializer):
    nonce = serializers.CharField(max_length=64)


class SubmitTxSerializer(serializers.Serializer):
    nonce = serializers.CharField(max_length=64)
    tx_hash = serializers.CharField(max_length=66)
    wallet_address = serializers.CharField(max_length=42)

    def validate_tx_hash(self, value):
        if not value.startswith("0x") or len(value) != 66:
            raise serializers.ValidationError("Invalid tx_hash format")
        return value.lower()
