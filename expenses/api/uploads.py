# django imports
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

# models import
from expenses.models import Upload
from expenses.serializers import UploadSerializer


class UploadViewSet(viewsets.ModelViewSet):
    queryset = Upload.objects.all()
    serializer_class = UploadSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ["end_date", "start_date"]
    ordering = ["-end_date"]

    @action(detail=False, methods=["delete"])
    def remove_unused_uploads(self, request, *args, **kwargs):
        unused_uploads = Upload.objects.annotate(num_expenses=Count("expense")).filter(num_expenses=0)
        deletes, _ = unused_uploads.delete()
        return Response(data={"files-removed": deletes}, status=status.HTTP_200_OK)
