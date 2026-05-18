"""Wallet views"""
import logging
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from core.response import APIResponse
from core.pagination import StandardResultsPagination
from .models import Wallet, WalletTransaction
from .serializers import WalletSerializer, WalletTransactionSerializer, DepositSerializer
from .services import WalletService

logger = logging.getLogger("nexuspay")


class WalletDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Wallet"], summary="Get wallet details and balances")
    def get(self, request):
        try:
            wallet = Wallet.objects.get(user=request.user)
        except Wallet.DoesNotExist:
            wallet = WalletService.create_wallet(request.user)
        return APIResponse.success(data=WalletSerializer(wallet).data)


class DepositView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment"

    @extend_schema(tags=["Wallet"], request=DepositSerializer, summary="Simulate deposit")
    def post(self, request):
        serializer = DepositSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(serializer.errors)

        wallet = Wallet.objects.get(user=request.user)
        data = serializer.validated_data
        tx = WalletService.simulate_deposit(
            wallet=wallet,
            currency=data["currency"],
            amount=data["amount"],
            actor=request.user,
        )
        return APIResponse.created(
            data=WalletTransactionSerializer(tx).data,
            message=f"Successfully deposited {data['amount']} {data['currency']}",
        )


class WalletTransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Wallet"],
        summary="List wallet transactions",
        parameters=[
            OpenApiParameter("currency", str, description="Filter by INR or USDT"),
            OpenApiParameter("category", str, description="Filter by transaction category"),
            OpenApiParameter("status", str, description="Filter by status"),
        ],
    )
    def get(self, request):
        wallet = Wallet.objects.get(user=request.user)
        qs = WalletTransaction.objects.filter(wallet=wallet)

        # Filters
        currency = request.query_params.get("currency")
        category = request.query_params.get("category")
        status = request.query_params.get("status")
        if currency:
            qs = qs.filter(currency=currency.upper())
        if category:
            qs = qs.filter(category=category.upper())
        if status:
            qs = qs.filter(status=status.upper())

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = WalletTransactionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class WalletTransactionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Wallet"], summary="Get single transaction detail")
    def get(self, request, tx_id):
        try:
            wallet = Wallet.objects.get(user=request.user)
            tx = WalletTransaction.objects.get(id=tx_id, wallet=wallet)
        except (Wallet.DoesNotExist, WalletTransaction.DoesNotExist):
            return APIResponse.not_found("Transaction not found")
        return APIResponse.success(data=WalletTransactionSerializer(tx).data)


class Web3ConnectView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Wallet"], summary="Link Web3 wallet via signature verification")
    def post(self, request):
        from eth_account.messages import encode_defunct
        from eth_account import Account

        address = request.data.get("address")
        message = request.data.get("message")
        signature = request.data.get("signature")

        if not all([address, message, signature]):
            return APIResponse.error("address, message, and signature are required", status_code=400)

        try:
            # Verify signature matches the message and was signed by the address
            signable_message = encode_defunct(text=message)
            recovered_address = Account.recover_message(signable_message, signature=signature)

            if recovered_address.lower() != address.lower():
                return APIResponse.error("Signature verification failed. Address mismatch.", status_code=401)

            # Link address to wallet
            wallet = Wallet.objects.get(user=request.user)
            
            # Check if address is already linked to another wallet
            if Wallet.objects.filter(web3_address__iexact=address).exclude(id=wallet.id).exists():
                return APIResponse.error("This wallet address is already linked to another account.", status_code=400)

            wallet.web3_address = address
            wallet.save(update_fields=["web3_address", "updated_at"])
            
            logger.info(f"[WEB3] User {request.user.email} successfully linked wallet {address}")
            return APIResponse.success(message=f"Web3 wallet {address} linked successfully!")

        except Exception as e:
            logger.error(f"[WEB3 ERROR] Failed to link wallet for {request.user.email}: {e}")
            return APIResponse.error(f"Failed to verify signature: {str(e)}", status_code=400)
