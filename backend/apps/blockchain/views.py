"""Blockchain app views"""
import logging
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from core.response import APIResponse
from core.blockchain.provider import get_provider
from .models import BlockchainTransaction, SettlementEvent
from .serializers import BlockchainTransactionSerializer, SettlementEventSerializer

logger = logging.getLogger("nexuspay.blockchain")


class BlockchainTransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Blockchain"], summary="List blockchain transactions for current user")
    def get(self, request):
        from apps.wallet.models import Wallet
        try:
            wallet = Wallet.objects.get(user=request.user)
            web3_address = wallet.web3_address
        except Wallet.DoesNotExist:
            web3_address = None

        if not web3_address:
            return APIResponse.success(data={"results": [], "count": 0})

        qs = BlockchainTransaction.objects.filter(
            from_address__iexact=web3_address
        ).order_by("-submitted_at")[:50]

        return APIResponse.success(data={
            "results": BlockchainTransactionSerializer(qs, many=True).data,
            "count": qs.count(),
        })


class BlockchainTransactionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Blockchain"], summary="Get transaction detail and live confirmation status")
    def get(self, request, tx_hash):
        try:
            tx = BlockchainTransaction.objects.get(tx_hash__iexact=tx_hash)
        except BlockchainTransaction.DoesNotExist:
            # Not indexed yet — query blockchain directly
            provider = get_provider()
            response = provider.get_transaction_receipt(tx_hash)
            if not response.success or response.data is None:
                return APIResponse.not_found("Transaction not found")
            return APIResponse.success(data={
                "tx_hash": tx_hash,
                "status": "MEMPOOL_PENDING",
                "provider_used": response.provider_used,
                "indexed": False,
            })

        return APIResponse.success(data=BlockchainTransactionSerializer(tx).data)


class SubmitBlockchainTransactionView(APIView):
    """
    Called by the frontend AFTER MetaMask broadcasts a transaction.
    Backend records the tx_hash and begins monitoring confirmations.
    Backend NEVER submits transactions itself.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Blockchain"], summary="Submit tx_hash for monitoring after MetaMask broadcast")
    def post(self, request):
        from apps.wallet.models import Wallet
        tx_hash = request.data.get("tx_hash", "").strip()
        qr_nonce = request.data.get("qr_nonce", "").strip()
        payment_intent_id = request.data.get("payment_intent_id", "").strip()
        from_address = request.data.get("from_address", "").strip()
        to_address = request.data.get("to_address", "").strip()
        amount = request.data.get("amount")

        if not tx_hash or not tx_hash.startswith("0x") or len(tx_hash) != 66:
            return APIResponse.error("Valid tx_hash (0x..., 66 chars) is required", status_code=400)

        if BlockchainTransaction.objects.filter(tx_hash__iexact=tx_hash).exists():
            return APIResponse.error("Transaction already being monitored", status_code=409)

        # Validate sender matches linked wallet
        try:
            wallet = Wallet.objects.get(user=request.user)
            if wallet.web3_address and from_address:
                if wallet.web3_address.lower() != from_address.lower():
                    return APIResponse.error(
                        "Transaction sender does not match your linked wallet", status_code=403
                    )
        except Wallet.DoesNotExist:
            pass

        bc_config = request.parser_context.get("kwargs", {})
        from django.conf import settings
        config = settings.BLOCKCHAIN_CONFIG

        try:
            from decimal import Decimal
            tx = BlockchainTransaction.objects.create(
                tx_hash=tx_hash.lower(),
                from_address=(from_address or "").lower(),
                to_address=(to_address or "").lower(),
                token_contract=config["USDC_CONTRACT_ADDRESS"].lower(),
                token_symbol=config["USDC_TOKEN_SYMBOL"],
                amount_raw=str(amount or 0),
                amount_human=Decimal(str(amount or 0)),
                chain_id=config["CHAIN_ID"],
                required_confirmations=config["REQUIRED_CONFIRMATIONS"],
                qr_code_nonce=qr_nonce,
                payment_intent_id=payment_intent_id or None,
                status="SUBMITTED",
            )

            # Immediately trigger monitoring
            from .tasks import poll_pending_transactions
            poll_pending_transactions.delay()

            logger.info(
                f"[BLOCKCHAIN] Registered tx {tx_hash[:12]}... for user {request.user.email}"
            )

            return APIResponse.created(
                data=BlockchainTransactionSerializer(tx).data,
                message="Transaction registered. Monitoring confirmations.",
            )
        except Exception as e:
            logger.error(f"[BLOCKCHAIN] Failed to register tx: {e}")
            return APIResponse.error(str(e), status_code=400)


class BlockchainHealthView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(tags=["Blockchain"], summary="Provider health check (admin only)")
    def get(self, request):
        provider = get_provider()
        health = provider.health_check()
        return APIResponse.success(data=health)


class UserSettlementsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Blockchain"], summary="List settlement events for current user")
    def get(self, request):
        settlements = SettlementEvent.objects.filter(
            user=request.user
        ).order_by("-created_at")[:50]
        return APIResponse.success(data=SettlementEventSerializer(settlements, many=True).data)
