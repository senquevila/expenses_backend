# django imports
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

# models import
from expenses.models import Loan
from expenses.serializers import (
    LoanReaderSerializer,
    LoanWriterSerializer,
)


class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    filter_backends = [OrderingFilter]
    ordering_fields = ["start_date", "end_date", "amount", "monthly_payment"]
    ordering = ["-amount"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return LoanReaderSerializer
        return LoanWriterSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        is_active = self.request.query_params.get("is_active")
        if is_active is None:
            return queryset

        is_active = is_active.lower()
        if is_active in ("true", "1", "yes"):
            return queryset.filter(is_active=True)
        if is_active in ("false", "0", "no"):
            return queryset.filter(is_active=False)
        return queryset

    @action(detail=True, methods=["post"], url_path="toggle")
    def toggle_active(self, request, *args, **kwargs):
        loan = self.get_object()
        loan.is_active = not loan.is_active
        loan.save()
        return Response({"status": "success", "is_active": loan.is_active})

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request, *args, **kwargs):
        active_loans = Loan.objects.filter(is_active=True).select_related("currency")
        today = timezone.now().date()
        total_monthly = Decimal(0)
        total_remaining = Decimal(0)

        for loan in active_loans:
            local_monthly = loan.get_local_monthly_payment
            total_monthly += local_monthly
            end_date = loan.end_date
            if end_date > today:
                diff = relativedelta(end_date, today)
                remaining_months = diff.years * 12 + diff.months
            else:
                remaining_months = 0
            total_remaining += local_monthly * remaining_months

        currency = settings.DEFAULT_CURRENCY
        return Response(
            {
                "monthly": {"value": total_monthly, "currency": currency},
                "remaining": {"value": total_remaining, "currency": currency},
            }
        )
