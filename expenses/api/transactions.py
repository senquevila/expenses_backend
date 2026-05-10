# django imports
from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

# models import
from expenses.models import Transaction
from expenses.serializers import (
    TransactionReadSerializer,
    TransactionWriteSerializer,
)


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    filter_backends = [OrderingFilter]
    ordering_fields = ["payment_date", "amount", "local_amount"]
    ordering = ["-payment_date", "-local_amount"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return TransactionReadSerializer
        return TransactionWriteSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")

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
