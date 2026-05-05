# django imports
from decimal import Decimal

from django.conf import settings
from django.db.models import F
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

# models import
from expenses.models import Subscription
from expenses.serializers import (
    SubscriptionReaderSerializer,
    SubscriptionWriteSerializer,
)


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    filter_backends = [OrderingFilter]
    ordering_fields = ["name", "monthly_payment"]
    ordering = ["-monthly_payment"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return SubscriptionReaderSerializer
        return SubscriptionWriteSerializer

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
        subscription = self.get_object()
        Subscription.objects.filter(pk=subscription.pk).update(is_active=~F("is_active"))
        subscription.refresh_from_db(fields=["is_active"])
        return Response({"status": "success", "is_active": subscription.is_active})

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request, *args, **kwargs):
        active = Subscription.objects.filter(is_active=True).select_related("currency")
        total = sum((s.get_local_monthly_payment for s in active), Decimal(0))
        return Response({"total": {"value": total, "currency": settings.DEFAULT_CURRENCY}})
