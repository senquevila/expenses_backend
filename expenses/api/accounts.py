from django.db import transaction
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter

from expenses.models import Account, AccountAssociation, Transaction
from expenses.serializers import (
    AccountAssociationReadSerializer,
    AccountAssociationWriteSerializer,
    AccountReadSerializer,
    AccountTransferSerializer,
    AccountWriteSerializer,
)
from expenses.utils.tools import change_account_from_assoc


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return AccountReadSerializer
        return AccountWriteSerializer

    @action(detail=False, methods=["post"])
    def transfer(self, request):
        serializer = AccountTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source = serializer.validated_data["source_account_id"]
        target = serializer.validated_data["target_account_id"]

        with transaction.atomic():
            Transaction.objects.filter(account_id=source.id).update(account_id=target.id)
            source.delete()

        return JsonResponse(data={"message": "Account transfer successful"}, status=200)


class AccountAssociationViewSet(viewsets.ModelViewSet):
    queryset = AccountAssociation.objects.all()
    serializer_class = AccountAssociationReadSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ["account__name"]
    ordering = ["account__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        account_id = self.request.query_params.get("account")
        if account_id is not None:
            queryset = queryset.filter(account_id=account_id)

        token = self.request.query_params.get("token")
        if token is not None:
            queryset = queryset.filter(token=token)
        return queryset

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return AccountAssociationReadSerializer
        return AccountAssociationWriteSerializer

    @action(detail=False, methods=["post"])
    def execute(self, request):
        data = change_account_from_assoc()
        return JsonResponse(data={"updated": len(data), "transactions": data}, status=200)
