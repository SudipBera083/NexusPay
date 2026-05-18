"""Admin panel views — user management, transaction monitoring, fraud detection"""
import logging
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from core.response import APIResponse
from core.permissions import IsAdminUser
from core.pagination import StandardResultsPagination
from apps.authentication.models import User
from apps.wallet.models import Wallet, WalletTransaction, AuditLog
from apps.transactions.models import ConversionHistory, PaymentTransaction
from apps.exchange.models import ExchangeRate
from apps.exchange.services import RateService

logger = logging.getLogger("nexuspay")


class AdminUserListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=["Admin"], summary="List all users")
    def get(self, request):
        from apps.authentication.serializers import UserProfileSerializer
        qs = User.objects.select_related("wallet").order_by("-date_joined")

        search = request.query_params.get("search")
        role = request.query_params.get("role")
        is_verified = request.query_params.get("is_verified")

        if search:
            qs = qs.filter(Q(email__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search))
        if role:
            qs = qs.filter(role=role.upper())
        if is_verified is not None:
            qs = qs.filter(is_verified=is_verified.lower() == "true")

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(UserProfileSerializer(page, many=True).data)


class AdminUserDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=["Admin"], summary="Get user + wallet details")
    def get(self, request, user_id):
        from apps.authentication.serializers import UserProfileSerializer
        from apps.wallet.serializers import WalletSerializer
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return APIResponse.not_found("User not found")

        wallet = getattr(user, "wallet", None)
        return APIResponse.success(data={
            "user": UserProfileSerializer(user).data,
            "wallet": WalletSerializer(wallet).data if wallet else None,
        })

    @extend_schema(tags=["Admin"], summary="Update user role or status")
    def patch(self, request, user_id):
        from apps.authentication.serializers import UserProfileSerializer
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return APIResponse.not_found("User not found")

        allowed_fields = {"is_active", "role", "kyc_status", "is_verified"}
        for field in allowed_fields:
            if field in request.data:
                setattr(user, field, request.data[field])
        user.save()

        AuditLog.log(
            actor=request.user,
            action="ADMIN_USER_UPDATE",
            resource_type="User",
            resource_id=str(user.id),
            after=request.data,
            request=request,
        )
        return APIResponse.success(data=UserProfileSerializer(user).data, message="User updated")


class AdminWalletInspectView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=["Admin"], summary="Inspect wallet by user ID")
    def get(self, request, user_id):
        from apps.wallet.serializers import WalletSerializer, WalletTransactionSerializer
        try:
            wallet = Wallet.objects.get(user_id=user_id)
        except Wallet.DoesNotExist:
            return APIResponse.not_found("Wallet not found")

        recent_txs = WalletTransaction.objects.filter(wallet=wallet).order_by("-created_at")[:20]
        return APIResponse.success(data={
            "wallet": WalletSerializer(wallet).data,
            "recent_transactions": WalletTransactionSerializer(recent_txs, many=True).data,
        })

    @extend_schema(tags=["Admin"], summary="Lock/unlock wallet")
    def patch(self, request, user_id):
        from apps.wallet.serializers import WalletSerializer
        try:
            wallet = Wallet.objects.get(user_id=user_id)
        except Wallet.DoesNotExist:
            return APIResponse.not_found("Wallet not found")

        action = request.data.get("action")
        if action == "lock":
            wallet.is_locked = True
            wallet.lock_reason = request.data.get("reason", "Admin lock")
            wallet.save(update_fields=["is_locked", "lock_reason"])
            msg = "Wallet locked"
        elif action == "unlock":
            wallet.is_locked = False
            wallet.lock_reason = ""
            wallet.save(update_fields=["is_locked", "lock_reason"])
            msg = "Wallet unlocked"
        else:
            return APIResponse.error("Action must be 'lock' or 'unlock'")

        AuditLog.log(actor=request.user, action=f"WALLET_{action.upper()}", resource_type="Wallet",
                     resource_id=str(wallet.id), request=request)
        return APIResponse.success(data=WalletSerializer(wallet).data, message=msg)


class AdminTransactionMonitorView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=["Admin"], summary="Monitor all transactions")
    def get(self, request):
        from apps.wallet.serializers import WalletTransactionSerializer
        qs = WalletTransaction.objects.select_related("wallet__user").order_by("-created_at")

        status_filter = request.query_params.get("status")
        currency = request.query_params.get("currency")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        if currency:
            qs = qs.filter(currency=currency.upper())

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(WalletTransactionSerializer(page, many=True).data)


class AdminReverseTransactionView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=["Admin"], summary="Reverse a transaction")
    def post(self, request, tx_id):
        from apps.wallet.services import WalletService
        from apps.wallet.serializers import WalletTransactionSerializer
        try:
            reversal = WalletService.reverse_transaction(tx_id=str(tx_id), actor=request.user)
            AuditLog.log(actor=request.user, action="TRANSACTION_REVERSED", resource_type="WalletTransaction",
                         resource_id=str(tx_id), request=request)
            return APIResponse.success(
                data=WalletTransactionSerializer(reversal).data,
                message="Transaction reversed successfully",
            )
        except Exception as e:
            return APIResponse.error(str(e))


class AdminStatsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=["Admin"], summary="Platform-wide statistics")
    def get(self, request):
        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0)

        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        verified_users = User.objects.filter(is_verified=True).count()

        total_inr = Wallet.objects.aggregate(total=Sum("inr_balance"))["total"] or 0
        total_usdt = Wallet.objects.aggregate(total=Sum("usdt_balance"))["total"] or 0

        today_payments = PaymentTransaction.objects.filter(created_at__gte=today)
        today_revenue = today_payments.aggregate(total=Sum("amount_inr"))["total"] or 0

        today_conversions = ConversionHistory.objects.filter(created_at__gte=today)
        total_fees = today_conversions.aggregate(total=Sum("fee_amount"))["total"] or 0

        # Fraud signals: large transactions in short time
        suspicious = WalletTransaction.objects.filter(
            amount__gte=Decimal("10000"),
            created_at__gte=now - timedelta(hours=1),
        ).count()

        rate_obj = RateService.get_current_rate("USDT_INR")

        return APIResponse.success(data={
            "users": {
                "total": total_users,
                "active": active_users,
                "verified": verified_users,
            },
            "balances": {
                "total_inr_in_system": str(total_inr),
                "total_usdt_in_system": str(total_usdt),
            },
            "today": {
                "payment_volume_inr": str(today_revenue),
                "payment_count": today_payments.count(),
                "conversion_fees_collected": str(total_fees),
                "conversions": today_conversions.count(),
            },
            "fraud": {
                "suspicious_large_transactions_last_hour": suspicious,
            },
            "exchange": {
                "current_usdt_inr": str(rate_obj.rate) if rate_obj else None,
            },
        })


class AdminAuditLogView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=["Admin"], summary="View audit logs")
    def get(self, request):
        from apps.wallet.serializers import AuditLogSerializer
        qs = AuditLog.objects.select_related("actor").order_by("-timestamp")
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(AuditLogSerializer(page, many=True).data)


class AdminSetExchangeRateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=["Admin"], summary="Manually override exchange rate")
    def post(self, request):
        from apps.exchange.views import ExchangeRateSerializer
        from rest_framework import serializers as drf_serializers

        class RateOverrideSerializer(drf_serializers.Serializer):
            rate = drf_serializers.DecimalField(max_digits=20, decimal_places=8)
            spread = drf_serializers.DecimalField(max_digits=5, decimal_places=4, required=False)

        ser = RateOverrideSerializer(data=request.data)
        if not ser.is_valid():
            return APIResponse.validation_error(ser.errors)

        rate_obj = ExchangeRate.objects.create(
            currency_pair="USDT_INR",
            rate=ser.validated_data["rate"],
            spread=ser.validated_data.get("spread", Decimal("0.5")),
            source="Admin Override",
        )

        AuditLog.log(actor=request.user, action="EXCHANGE_RATE_OVERRIDE", resource_type="ExchangeRate",
                     resource_id=str(rate_obj.id), after={"rate": str(rate_obj.rate)}, request=request)

        return APIResponse.created(
            data=ExchangeRateSerializer(rate_obj).data,
            message="Exchange rate overridden",
        )
