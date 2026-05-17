# django imports
from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

# models import
from expenses.models import ProgramTransaction, Transaction
from expenses.serializers import (
    ProgramTransactionReadSerializer,
    ProgramTransactionWriteSerializer,
    TransactionReadSerializer,
    TransactionWriteSerializer,
)


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    filter_backends = [OrderingFilter]
    ordering_fields = ["payment_date", "amount", "local_amount", "created"]
    ordering = ["-payment_date", "-created"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return TransactionReadSerializer
        return TransactionWriteSerializer

    def get_queryset(self):
        queryset = super().get_queryset().valid()
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")
        upload = self.request.query_params.get("upload")
        account = self.request.query_params.get("account")
        period = self.request.query_params.get("period")

        if year is not None:
            try:
                queryset = queryset.filter(payment_date__year=int(year))
            except (TypeError, ValueError):
                raise ValidationError({"year": "Must be a valid integer."})

        if month is not None:
            try:
                queryset = queryset.filter(payment_date__month=int(month))
            except (TypeError, ValueError):
                raise ValidationError({"month": "Must be a valid integer."})

        if upload is not None:
            try:
                queryset = queryset.filter(upload_id=int(upload))
            except (TypeError, ValueError):
                raise ValidationError({"upload": "Must be a valid integer."})

        if period is not None:
            try:
                queryset = queryset.filter(period_id=int(period))
            except (TypeError, ValueError):
                raise ValidationError({"period": "Must be a valid integer."})

        if account is not None:
            try:
                queryset = queryset.filter(account_id=int(account))
            except (TypeError, ValueError):
                raise ValidationError({"account": "Must be a valid integer."})

        description = self.request.query_params.get("description")
        if description:
            queryset = queryset.filter(description__icontains=description)

        return queryset

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


class ProgramTransactionViewSet(viewsets.ModelViewSet):
    queryset = ProgramTransaction.objects.all()
    filter_backends = [OrderingFilter]
    ordering_fields = ["start_date", "end_date", "amount"]
    ordering = ["-start_date"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return ProgramTransactionReadSerializer
        return ProgramTransactionWriteSerializer
