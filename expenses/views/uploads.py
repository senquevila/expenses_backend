import csv
import json
from io import StringIO
from typing import Any

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.generic import FormView, ListView, TemplateView

from expenses.forms import (
    TransactionInspectionForm,
    UploadForm,
    UploadTransformAccountForm,
    UploadTransformForm,
)
from expenses.models import Account, Transaction, Upload
from expenses.serializers import UploadSerializer
from expenses.utils.uploads import process_account_csv, process_credit_card_csv


class UploadListView(ListView):
    template_name = "expenses/upload_list.html"
    serializer_class = UploadSerializer
    context_object_name = "uploads"

    def get_queryset(self):
        uploads = Upload.objects.order_by("-id")
        for upload in uploads:
            upload.trx_count = Transaction.objects.filter(upload=upload).count()
            upload.line_count = upload.parameters["rows"]["end"] - upload.parameters["rows"]["start"]
        return uploads


class UploadAddView(FormView):
    template_name = "expenses/upload_add.html"
    form_class = UploadForm

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        file = form.cleaned_data["file"]
        file_type = form.cleaned_data["file_type"]

        if not file:
            form.add_error(None, "File empty")
            return self.form_invalid(form)

        if not file_type:
            form.add_error(None, "File type not selected")
            return self.form_invalid(form)

        upload = form.save()

        # create a dictionary with the file rows and columns
        file.seek(0)
        decoded_file = file.read().decode("iso-8859-1")

        csv_file = StringIO(decoded_file)
        reader = csv.reader(csv_file)

        data = []
        key = 0
        num_cols = 0
        # Fill the dictionary with data, using one of the fields (e.g., name) as the key
        for row in reader:
            l_row = list(row)
            l_row.insert(0, key)
            data.append(l_row)
            num_cols = max(num_cols, len(l_row))
            key += 1

        num_rows = key + 1

        upload.dimension = {
            "rows": num_rows,
            "cols": num_cols,
        }
        upload.data = data
        upload.save()

        if file_type == "credit_card":
            page = "upload-transform-credit-card"
        elif file_type == "account":
            page = "upload-transform-account"
        else:
            page = "upload-add"

        return HttpResponseRedirect(reverse(page, args=(upload.id,)))


class UploadTransformCreditCardView(FormView):
    template_name = "expenses/upload_transform_credit_card.html"
    form_class = UploadTransformForm

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        upload = Upload.objects.get(pk=self.kwargs.get("pk"))
        context["file"] = upload.file
        context["rows"] = upload.data
        context["dimension"] = upload.dimension
        return context

    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        upload = Upload.objects.get(pk=self.kwargs.get("pk"))
        form = self.get_form()

        if form.is_valid():
            upload.parameters["rows"]["start"] = form.cleaned_data["start_row"]
            upload.parameters["rows"]["end"] = form.cleaned_data["end_row"]
            upload.parameters["cols"] = [
                {"payment_date": form.cleaned_data["payment_date"]},
                {"description": form.cleaned_data["description"]},
                {"amount": form.cleaned_data["amount"]},
                {"amount_currency": form.cleaned_data["amount_currency"]},
            ]
            upload.save()

            # process the csv content
            process_credit_card_csv(upload)

            return HttpResponseRedirect(reverse("upload-inspect", args=(upload.id,)))

        return self.form_invalid(form)  # Handle invalid form submission


class UploadTransformAccountView(FormView):
    template_name = "expenses/upload_transform_account.html"
    form_class = UploadTransformAccountForm

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        upload = Upload.objects.get(pk=self.kwargs.get("pk"))
        context["file"] = upload.file
        context["rows"] = upload.data
        context["dimension"] = upload.dimension
        return context

    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        upload = Upload.objects.get(pk=self.kwargs.get("pk"))
        form = self.get_form()

        if form.is_valid():
            upload.parameters["rows"]["start"] = form.cleaned_data["start_row"]
            upload.parameters["rows"]["end"] = form.cleaned_data["end_row"]
            upload.parameters["cols"] = [
                {"payment_date": form.cleaned_data["payment_date"]},
                {"description": form.cleaned_data["description"]},
                {"amount_debit": form.cleaned_data["amount_debit"]},
                {"amount_credit": form.cleaned_data["amount_credit"]},
            ]
            upload.save()

            # process the csv content
            process_account_csv(upload, form.cleaned_data["currency"])

            return HttpResponseRedirect(reverse("upload-inspect", args=(upload.id,)))

        return self.form_invalid(form)  # Handle invalid form submission


class UploadResultView(TemplateView):
    """
    Show the content of the uploaded file and their status result.
    Status:
        - created
        - duplicated
        - period not found or closed
    """

    template_name = "expenses/upload_result.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        try:
            upload = Upload.objects.get(pk=self.kwargs.get("pk"))
            data = json.loads(upload.result)
            context.update(data)
            context["upload"] = upload
        except Upload.DoesNotExist:
            pass

        return context


class UploadInspectView(TemplateView):
    """
    Edit the transaction account given in the upload process.
    """

    template_name = "expenses/upload_inspect.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        try:
            upload = Upload.objects.get(pk=self.kwargs.get("pk"))
            transactions = Transaction.objects.filter(upload=upload)
            context["upload"] = upload
            context["transactions"] = transactions
            context["accounts"] = Account.objects.order_by("name")
        except Upload.DoesNotExist:
            pass

        return context

    def post(self, request, *args, **kwargs):
        transaction = Transaction.objects.get(pk=request.POST.get("transaction_id"))
        form = TransactionInspectionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            return JsonResponse({"success": True})
        return JsonResponse({"success": False, "errors": form.errors})
