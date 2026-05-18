"""Transaction views"""
import logging
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from core.response import APIResponse
from core.pagination import StandardResultsPagination
from apps.notifications.tasks import notify_transaction
from .models import ConversionHistory, PaymentTransaction
from .serializers import (
    ConversionHistorySerializer, PaymentTransactionSerializer,
    ConvertRequestSerializer, PaymentRequestSerializer,
)
from .services import ConversionService, PaymentService

logger = logging.getLogger("nexuspay")


class ConvertView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "conversion"

    @extend_schema(tags=["Transactions"], request=ConvertRequestSerializer, summary="Convert INR ↔ USDT")
    def post(self, request):
        serializer = ConvertRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(serializer.errors)

        d = serializer.validated_data
        conversion = ConversionService.convert(
            user=request.user,
            from_currency=d["from_currency"],
            to_currency=d["to_currency"],
            amount=d["amount"],
        )

        # Async notification
        notify_transaction.delay(
            user_id=str(request.user.id),
            event_type="CONVERSION",
            data={
                "from": f"{d['amount']} {d['from_currency']}",
                "to": f"{conversion.to_amount} {d['to_currency']}",
                "reference_id": conversion.reference_id,
            },
        )

        return APIResponse.created(
            data=ConversionHistorySerializer(conversion).data,
            message=f"Successfully converted {d['amount']} {d['from_currency']} → {conversion.to_amount} {d['to_currency']}",
        )


class ConversionHistoryListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Transactions"], summary="List conversion history")
    def get(self, request):
        qs = ConversionHistory.objects.filter(user=request.user)
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ConversionHistorySerializer(page, many=True).data)


class PaymentView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment"

    @extend_schema(tags=["Transactions"], request=PaymentRequestSerializer, summary="Make a merchant payment")
    def post(self, request):
        serializer = PaymentRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(serializer.errors)

        d = serializer.validated_data
        payment = PaymentService.process_payment(
            user=request.user,
            merchant_name=d["merchant_name"],
            amount_inr=d["amount_inr"],
            description=d.get("description", ""),
            merchant_category=d.get("merchant_category", "General"),
        )

        notify_transaction.delay(
            user_id=str(request.user.id),
            event_type="PAYMENT",
            data={
                "merchant": d["merchant_name"],
                "amount": f"₹{d['amount_inr']}",
                "reference_id": payment.reference_id,
            },
        )

        return APIResponse.created(
            data=PaymentTransactionSerializer(payment).data,
            message=f"Payment of ₹{d['amount_inr']} to {d['merchant_name']} successful",
        )


class PaymentHistoryListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Transactions"], summary="List payment history")
    def get(self, request):
        qs = PaymentTransaction.objects.filter(user=request.user)
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(PaymentTransactionSerializer(page, many=True).data)
