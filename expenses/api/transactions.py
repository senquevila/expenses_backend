# django imports
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

# models import
from expenses.models import Loan, Subscription, Transaction, Upload
from expenses.serializers import (
    LoanReaderSerializer,
    LoanWriterSerializer,
    SubscriptionReaderSerializer,
    SubscriptionWriteSerializer,
    TransactionReadSerializer,
    TransactionWriteSerializer,
    UploadSerializer,
)


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return TransactionReadSerializer
        return TransactionWriteSerializer

    def destroy(self, request, *args, **kwargs):
        transaction = self.get_object()
        if transaction.period.closed:
            return Response(
                {"detail": "The selected period is closed and cannot be modified."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["delete"])
    def remove_invalid_expenses(self, request, *args, **kwargs):
        invalid_expenses = Transaction.objects.filter(account__name=settings.INVALID_ACCOUNT)
        deletes, _ = invalid_expenses.delete()
        return Response(data={"transaction-removed": deletes}, status=status.HTTP_200_OK)


class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()

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
        return Response({
            "monthly": {"value": total_monthly, "currency": currency},
            "remaining": {"value": total_remaining, "currency": currency},
        })


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()

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
        subscription.is_active = not subscription.is_active
        subscription.save()
        return Response({"status": "success", "is_active": subscription.is_active})

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request, *args, **kwargs):
        active = Subscription.objects.filter(is_active=True).select_related("currency")
        total = sum((s.get_local_monthly_payment for s in active), Decimal(0))
        return Response({"total": {"value": total, "currency": settings.DEFAULT_CURRENCY}})


class UploadViewSet(viewsets.ModelViewSet):
    queryset = Upload.objects.all()
    serializer_class = UploadSerializer

    @action(detail=False, methods=["delete"])
    def remove_unused_uploads(self, request, *args, **kwargs):
        unused_uploads = Upload.objects.annotate(num_expenses=Count("expense")).filter(num_expenses=0)
        deletes, _ = unused_uploads.delete()
        return Response(data={"files-removed": deletes}, status=status.HTTP_200_OK)
