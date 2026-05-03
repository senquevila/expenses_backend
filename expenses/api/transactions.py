# django imports
from django.conf import settings
from django.db.models import Count
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


class UploadViewSet(viewsets.ModelViewSet):
    queryset = Upload.objects.all()
    serializer_class = UploadSerializer

    @action(detail=False, methods=["delete"])
    def remove_unused_uploads(self, request, *args, **kwargs):
        unused_uploads = Upload.objects.annotate(num_expenses=Count("expense")).filter(num_expenses=0)
        deletes, _ = unused_uploads.delete()
        return Response(data={"files-removed": deletes}, status=status.HTTP_200_OK)
