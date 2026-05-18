"""Dashboard analytics views"""
import logging
from decimal import Decimal
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from core.response import APIResponse
from apps.wallet.models import Wallet, WalletTransaction
from apps.transactions.models import ConversionHistory, PaymentTransaction
from apps.exchange.services import RateService

logger = logging.getLogger("nexuspay")


class DashboardOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Dashboard"], summary="Get dashboard overview")
    def get(self, request):
        user = request.user
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        try:
            wallet = Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            from apps.wallet.services import WalletService
            wallet = WalletService.create_wallet(user)

        # Get live rate
        rate_obj = RateService.get_current_rate("USDT_INR")
        rate = rate_obj.rate if rate_obj else Decimal("84.50")

        # Total portfolio value in INR
        portfolio_inr = wallet.inr_balance + (wallet.usdt_balance * rate)

        # Stats for 30 days
        tx_qs = WalletTransaction.objects.filter(wallet=wallet, created_at__gte=thirty_days_ago)
        total_debits = tx_qs.filter(transaction_type="DEBIT").aggregate(total=Sum("amount"))["total"] or 0
        total_credits = tx_qs.filter(transaction_type="CREDIT").aggregate(total=Sum("amount"))["total"] or 0

        payments_30d = PaymentTransaction.objects.filter(user=user, created_at__gte=thirty_days_ago)
        payment_total = payments_30d.aggregate(total=Sum("amount_inr"))["total"] or 0
        payment_count = payments_30d.count()

        conversions_30d = ConversionHistory.objects.filter(user=user, created_at__gte=thirty_days_ago)

        recent_txs = WalletTransaction.objects.filter(wallet=wallet).order_by("-created_at")[:5]
        from apps.wallet.serializers import WalletTransactionSerializer

        return APIResponse.success(data={
            "wallet": {
                "id": str(wallet.id),
                "inr_balance": str(wallet.inr_balance),
                "usdt_balance": str(wallet.usdt_balance),
                "portfolio_value_inr": str(portfolio_inr.quantize(Decimal("0.01"))),
            },
            "exchange": {
                "usdt_inr_rate": str(rate) if rate_obj else None,
                "buy_rate": str(rate_obj.buy_rate) if rate_obj else None,
                "sell_rate": str(rate_obj.sell_rate) if rate_obj else None,
            },
            "stats_30d": {
                "total_spent_inr": str(payment_total),
                "payment_count": payment_count,
                "conversion_count": conversions_30d.count(),
                "total_credits": str(total_credits),
                "total_debits": str(total_debits),
            },
            "recent_transactions": WalletTransactionSerializer(recent_txs, many=True).data,
        })


class SpendingAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Dashboard"], summary="Get spending analytics with chart data")
    def get(self, request):
        user = request.user
        days = int(request.query_params.get("days", 30))
        since = timezone.now() - timedelta(days=days)

        # Daily spending
        daily_spending = (
            PaymentTransaction.objects.filter(user=user, created_at__gte=since, status="COMPLETED")
            .annotate(day=TruncDay("created_at"))
            .values("day")
            .annotate(total=Sum("amount_inr"), count=Count("id"))
            .order_by("day")
        )

        # Category breakdown
        category_breakdown = (
            PaymentTransaction.objects.filter(user=user, created_at__gte=since, status="COMPLETED")
            .values("merchant_category")
            .annotate(total=Sum("amount_inr"), count=Count("id"))
            .order_by("-total")
        )

        # Conversion trend
        conversion_trend = (
            ConversionHistory.objects.filter(user=user, created_at__gte=since, status="COMPLETED")
            .annotate(day=TruncDay("created_at"))
            .values("day", "from_currency", "to_currency")
            .annotate(total_from=Sum("from_amount"), count=Count("id"))
            .order_by("day")
        )

        # Balance history (last N transactions)
        balance_history = (
            WalletTransaction.objects.filter(
                wallet__user=user, created_at__gte=since
            )
            .order_by("created_at")
            .values("created_at", "currency", "balance_after", "transaction_type")[:200]
        )

        return APIResponse.success(data={
            "period_days": days,
            "daily_spending": list(daily_spending),
            "category_breakdown": list(category_breakdown),
            "conversion_trend": list(conversion_trend),
            "balance_history": list(balance_history),
        })
