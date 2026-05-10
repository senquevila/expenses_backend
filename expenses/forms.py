from django import forms
from django.core.validators import FileExtensionValidator

from expenses.models import (
    Account,
    Currency,
    Loan,
    Period,
    Subscription,
    Transaction,
    Upload,
)


class AccountTransferForm(forms.Form):
    account_origin = forms.ModelChoiceField(queryset=Account.objects.order_by("name"))
    account_destination = forms.ModelChoiceField(queryset=Account.objects.order_by("name"))

    def clean(self):
        cleaned_data = super().clean()
        account_origin = cleaned_data.get("account_origin")
        account_destination = cleaned_data.get("account_destination")

        if account_origin == account_destination:
            raise forms.ValidationError("Accounts cannot be the same")

        return cleaned_data


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            "description",
            "payment_date",
            "period",
            "account",
            "currency",
            "amount",
        ]


class TransactionUploadForm(forms.Form):
    file = forms.FileField(
        label="Archivo",
        help_text="Seleccione un archivo CSV para cargar",
        validators=[FileExtensionValidator(allowed_extensions=["csv"])],
    )

    class Meta:
        model = Transaction
        fields = (
            "periodo",
            "description",
            "payment_date",
            "account",
            "currency",
            "amount",
            "created",
        )


class TransactionInspectionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ("account",)


class UploadForm(forms.ModelForm):
    file = forms.FileField(
        label="Archivo",
        help_text="Seleccione un archivo CSV para cargar",
        validators=[FileExtensionValidator(allowed_extensions=["csv"])],
    )
    file_type = forms.ChoiceField(
        label="Tipo de archivo",
        choices=(
            ("credit_card", "Tarjeta de crédito"),
            ("account", "Cuenta bancaria"),
        ),
    )

    class Meta:
        model = Upload
        fields = ("file", "file_type")


class UploadTransformForm(forms.ModelForm):
    start_row = forms.IntegerField(
        label="Start row",
        help_text="File number where the data starts",
        initial=0,
    )
    end_row = forms.IntegerField(
        label="End row",
        help_text="File number where the data ends",
        initial=0,
    )
    payment_date = forms.IntegerField(label="Date", initial=1)
    description = forms.IntegerField(label="Description", initial=2)
    amount = forms.IntegerField(label="Local", initial=3)
    amount_currency = forms.IntegerField(label="USD", initial=4)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _fields = [
            "start_row",
            "end_row",
            "payment_date",
            "description",
            "amount",
            "amount_currency",
        ]

        for field in _fields[:2]:
            self.fields[field].widget.attrs["class"] = "form-control repaint-row-trigger"

        for field in _fields[2:]:
            self.fields[field].widget.attrs["class"] = "form-control repaint-col-trigger"

    class Meta:
        model = Upload
        fields = ()


class UploadTransformAccountForm(forms.ModelForm):
    start_row = forms.IntegerField(
        label="Start row",
        help_text="File number where the data starts",
        initial=0,
    )
    end_row = forms.IntegerField(
        label="End row",
        help_text="File number where the data ends",
        initial=0,
    )
    payment_date = forms.IntegerField(label="Date", initial=1)
    description = forms.IntegerField(label="Description", initial=2)
    amount_debit = forms.IntegerField(label="Debit", initial=3)
    amount_credit = forms.IntegerField(label="Credit", initial=4)
    currency = forms.ModelChoiceField(Currency.objects.all())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _fields = [
            "start_row",
            "end_row",
            "payment_date",
            "description",
            "currency",
            "amount_debit",
            "amount_credit",
        ]

        for field in _fields[:2]:
            self.fields[field].widget.attrs["class"] = "form-control repaint-row-trigger"

        for field in _fields[2:]:
            self.fields[field].widget.attrs["class"] = "form-control repaint-col-trigger"

    class Meta:
        model = Upload
        fields = ()


class PeriodForm(forms.ModelForm):
    class Meta:
        model = Period
        fields = ["month", "year", "closed", "total", "active"]


class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = "__all__"


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = "__all__"
