"""Wallet serializers"""
from decimal import Decimal
from rest_framework import serializers
from .models import Wallet, WalletTransaction, AuditLog


class WalletSerializer(serializers.ModelSerializer):
    user_email = serializers.ReadOnlyField(source="user.email")
    user_name = serializers.ReadOnlyField(source="user.full_name")

    class Meta:
        model = Wallet
        fields = [
            "id", "user_email", "user_name",
            "inr_balance", "usdt_balance", "web3_address",
            "is_active", "is_locked", "lock_reason",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user_email", "user_name", "created_at", "updated_at"]


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = [
            "id", "transaction_type", "currency", "category",
            "amount", "balance_before", "balance_after",
            "description", "reference_id", "status",
            "metadata", "created_at",
        ]
        read_only_fields = fields


class DepositSerializer(serializers.Serializer):
    currency = serializers.ChoiceField(choices=["INR", "USDT"])
    amount = serializers.DecimalField(max_digits=15, decimal_places=8, min_value=Decimal("0.01"))

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value


class WithdrawSerializer(serializers.Serializer):
    currency = serializers.ChoiceField(choices=["USDT"])
    amount = serializers.DecimalField(max_digits=15, decimal_places=8, min_value=Decimal("0.01"))

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.ReadOnlyField(source="actor.email")

    class Meta:
        model = AuditLog
        fields = ["id", "actor_email", "action", "resource_type", "resource_id",
                  "before_state", "after_state", "ip_address", "timestamp"]
        read_only_fields = fields
