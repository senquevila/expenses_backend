# django imports
from django.conf import settings
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

# models import
from expenses.models import Period, Transaction, Upload, Loan, Subscription
from expenses.serializers import (
    PeriodSerializer,
    TransactionSerializer,
    UploadSerializer,
    LoanSerializer,
    SubscriptionSerializer,
)


class PeriodViewSet(viewsets.ModelViewSet):
    queryset = Period.objects.all()
    serializer_class = PeriodSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

    @action(detail=False, methods=["delete"])
    def remove_invalid_expenses(self, request, *args, **kwargs):
        invalid_expenses = Transaction.objects.filter(account__name=settings.INVALID_ACCOUNT)
        deletes = invalid_expenses.count()
        invalid_expenses.delete()
        return Response(data={"transaction-removed": deletes}, status=status.HTTP_200_OK)


class UploadViewSet(viewsets.ModelViewSet):
    queryset = Upload.objects.all()
    serializer_class = UploadSerializer

    @action(detail=False, methods=["delete"])
    def remove_unused_uploads(self, request, *args, **kwargs):
        unused_uploads = Upload.objects.annotate(num_expenses=Count("expense")).filter(num_expenses=0)
        deletes = unused_uploads.count()
        unused_uploads.delete()
        return Response(data={"files-removed": deletes}, status=status.HTTP_200_OK)


class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.filter(is_active=True)
    serializer_class = LoanSerializer


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.filter(is_active=True)
    serializer_class = SubscriptionSerializer
