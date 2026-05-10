# django imports
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

# models import
from expenses.models import Upload
from expenses.serializers import (
    UploadSerializer,
    UploadStep1InputSerializer,
    UploadStep1Serializer,
    UploadStep2Serializer,
)
from expenses.services.uploads import process_upload_result


class UploadViewSet(viewsets.ModelViewSet):
    queryset = Upload.objects.all()
    serializer_class = UploadSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ["end_date", "start_date", "created"]
    ordering = ["-created"]

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
        This is the first step of the upload process. It receives the file and returns the file name and the number of
        rows in the file.
        """
        input_serializer = UploadStep1InputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        upload = Upload.objects.create(file=input_serializer.validated_data["file"])
        output_serializer = self.get_serializer(upload)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="step2")
    def post_upload_step2(self, request, pk=None, *args, **kwargs):
        """
        This is the second step of the upload process. It retrieves the Upload instance by ID, updates its result with
        the provided payload, and returns the updated upload data.
        """
        upload = self.get_object()
        input_serializer = UploadStep2Serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        upload.result = input_serializer.validated_data["result"]
        upload.upload_type = input_serializer.validated_data["upload_type"]
        upload.upload_status = Upload.UploadStatus.PROCESSING
        upload.save(update_fields=["result", "upload_type", "upload_status"])
        process_upload_result(upload)
        output_serializer = self.get_serializer(upload)
        return Response(output_serializer.data, status=status.HTTP_200_OK)
