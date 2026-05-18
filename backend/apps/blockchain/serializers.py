"""Blockchain serializers"""
from rest_framework import serializers
from .models import BlockchainTransaction, SettlementEvent


class BlockchainTransactionSerializer(serializers.ModelSerializer):
    confirmation_progress = serializers.ReadOnlyField()
    is_finalized = serializers.ReadOnlyField()

    class Meta:
        model = BlockchainTransaction
        fields = [
            "id", "tx_hash", "from_address", "to_address", "token_symbol",
            "amount_human", "chain_id", "block_number", "confirmations",
            "required_confirmations", "confirmation_progress", "status",
            "is_finalized", "submitted_via_provider", "gas_used",
            "submitted_at", "confirmed_at", "last_checked_at",
        ]
        read_only_fields = fields


class SettlementEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SettlementEvent
        fields = [
            "id", "usdc_amount", "fee_amount", "net_amount",
            "status", "settled_at", "created_at", "metadata",
        ]
        read_only_fields = fields
