# django imports
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

# models import
from expenses.models import Period
from expenses.serializers import (
    PeriodSerializer,
)


class PeriodViewSet(viewsets.ModelViewSet):
    queryset = Period.objects.filter(active=True).order_by("-year", "-month")
    serializer_class = PeriodSerializer

    @action(detail=True, methods=["post"], url_path="toggle")
    def toggle(self, request, pk=None):
        period = self.get_object()
        period.closed = not period.closed
        period.save(update_fields=["closed"])
        return Response({"status": "success", "closed": period.closed}, status=status.HTTP_200_OK)
