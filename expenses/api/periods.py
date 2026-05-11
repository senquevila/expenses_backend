# django imports
from decimal import Decimal

from django.conf import settings
from django.db.models import DecimalField, Sum
from django.db.models.functions import Coalesce
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

# models import
from expenses.models import Period, Transaction
from expenses.serializers import (
    PeriodSerializer,
)
from expenses.services.periods import calculate_period_total


class PeriodViewSet(viewsets.ModelViewSet):
    queryset = Period.objects.filter(active=True).order_by("-year", "-month")
    serializer_class = PeriodSerializer

    @action(detail=True, methods=["get"], url_path="summary")
    def summary(self, request, pk=None):
        """
        Returns transaction totals grouped by account for the specified period.

        URL: GET /periods/{id}/summary/

        Response (200):
            [
                {
                    "account_id": int,
                    "account_name": str,
                    "total": {"value": Decimal, "currency": str}
                },
                ...
            ]
        """
        period = self.get_object()
        rows = (
            Transaction.objects.filter(period=period)
            .valid()
            .values("account_id", "account__name")
            .annotate(
                total=Coalesce(
                    Sum("local_amount"), Decimal(0), output_field=DecimalField(max_digits=14, decimal_places=2)
                )
            )
            .order_by("-total")
        )
        currency = settings.DEFAULT_CURRENCY
        data = [
            {
                "account_id": row["account_id"],
                "account_name": row["account__name"],
                "total": {"value": row["total"], "currency": currency},
            }
            for row in rows
        ]
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="toggle")
    def toggle(self, request, pk=None):
        period = self.get_object()
        period.closed = not period.closed
        period.save(update_fields=["closed"])
        if period.closed:
            calculate_period_total(period)
        else:
            period.total = 0
            period.save(update_fields=["total"])
        return Response(
            {"status": "success", "closed": period.closed, "total": period.total}, status=status.HTTP_200_OK
        )
