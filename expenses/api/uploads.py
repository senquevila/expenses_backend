# django imports
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

# models import
from expenses.models import Upload
from expenses.serializers import UploadSerializer, UploadStep1Serializer


class UploadViewSet(viewsets.ModelViewSet):
    queryset = Upload.objects.all()
    serializer_class = UploadSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ["end_date", "start_date"]
    ordering = ["-end_date"]

    def get_serializer_class(self):
        if self.action == "post_upload_step1":
            return UploadStep1Serializer
        return super().get_serializer_class()

    @action(detail=False, methods=["delete"])
    def remove_unused_uploads(self, request, *args, **kwargs):
        unused_uploads = Upload.objects.annotate(num_expenses=Count("expense")).filter(num_expenses=0)
        deletes, _ = unused_uploads.delete()
        return Response(data={"files-removed": deletes}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="step1")
    def post_upload_step1(self, request, *args, **kwargs):
        """
        This is the first step of the upload process. It receives the file and returns the file name and the number of rows in the file.
        """
        file = request.FILES.get("file")
        if not file:
            return Response(data={"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        if not file.name.endswith(".csv"):
            return Response(data={"error": "File must be a CSV"}, status=status.HTTP_400_BAD_REQUEST)

        # Create a new upload instance
        upload = Upload.objects.create(file=file)
        serializer = self.get_serializer(upload)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=["post"], url_path="step2")
    def post_upload_step2(self, request, pk=None, *args, **kwargs):
        """
        This is the second step of the upload process. It retrieves the Upload instance by ID, marks its result as 'processed', and returns the updated upload data.
        """
        upload = self.get_object()
        upload.result = "processed"
        upload.save(update_fields=["result"])
        serializer = self.get_serializer(upload)
        return Response(serializer.data, status=status.HTTP_200_OK)
