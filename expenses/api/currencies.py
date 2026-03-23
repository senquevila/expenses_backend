# django drf imports
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

# models import
from expenses.models import Currency, CurrencyConvert
from expenses.serializers import CurrencySerializer, CurrencyConvertSerializer
from expenses.utils.tools import create_dollar_conversion


class CurrencyViewSet(viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer


class CurrencyConvertViewSet(viewsets.ModelViewSet):
    queryset = CurrencyConvert.objects.all()
    serializer_class = CurrencyConvertSerializer

    @action(detail=False, methods=["post"])
    def create_dollar(self, request, *args, **kwargs):
        data, _status = create_dollar_conversion()
        return Response(data, status=_status)


class CreateDollarConversionView(APIView):
    def post(self, request, *args, **kwargs):
        data, _status = create_dollar_conversion()
        return Response(data, status=_status)
