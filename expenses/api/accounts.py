from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.views import APIView

from expenses.models import Account
from expenses.serializers import AccountReadSerializer, AccountWriteSerializer
from expenses.utils.tools import change_account_from_assoc


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return AccountReadSerializer
        return AccountWriteSerializer


class AccountAssociationView(APIView):
    def post(self, request, *args, **kwargs):
        data = change_account_from_assoc()
        return JsonResponse(data=data, safe=False)
