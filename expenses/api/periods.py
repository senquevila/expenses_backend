# django imports
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

# models import
from expenses.models import Period
from expenses.serializers import (
    PeriodSerializer,
)
from expenses.services.periods import calculate_period_total


class PeriodViewSet(viewsets.ModelViewSet):
    queryset = Period.objects.filter(active=True).order_by("-year", "-month")
    serializer_class = PeriodSerializer

    @action(detail=True, methods=["post"], url_path="toggle")
    def toggle(self, request, pk=None):
        period = self.get_object()
        period.closed = not period.closed
        period.save(update_fields=["closed"])
        if period.closed:
            calculate_period_total(period)
        return Response({"status": "success", "closed": period.closed, "total": period.total}, status=status.HTTP_200_OK)
