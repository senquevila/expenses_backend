from django.conf import settings
from rest_framework import serializers

from expenses.models import (
    Account,
    AccountAssociation,
    Currency,
    CurrencyConvert,
    Loan,
    Period,
    Subscription,
    Transaction,
    Upload,
)


class CurrencyMixin:
    def get_currency_code(self, obj):
        currency = getattr(obj, "currency", None)
        return currency.alpha3 if currency is not None else settings.DEFAULT_CURRENCY


class AccountFlatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        exclude = ["parent"]
        ordering = ["account_type", "name"]


class AccountReadSerializer(serializers.ModelSerializer):
    parent = AccountFlatSerializer(read_only=True)

    class Meta:
        model = Account
        fields = "__all__"
        ordering = ["account_type", "name"]


class AccountWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = "__all__"
        ordering = ["account_type", "name"]


# Keep backward-compatible alias
AccountSerializer = AccountWriteSerializer


class AccountAssociationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountAssociation
        fields = "__all__"
        ordering = ["account__name"]


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = "__all__"


class CurrencyConvertSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyConvert
        fields = "__all__"


class PeriodSerializer(serializers.ModelSerializer):
    """
    Serializer for the Period model.
    """

    total = serializers.SerializerMethodField()

    def get_total(self, obj):
        return {"value": obj.total, "currency": settings.DEFAULT_CURRENCY}

    class Meta:
        model = Period
        fields = "__all__"
        ordering = ["-year", "-month"]


class TransactionReadSerializer(CurrencyMixin, serializers.ModelSerializer):
    """
    Read serializer for Transaction — expands all related objects.
    """

    period = PeriodSerializer(read_only=True)
    account = AccountReadSerializer(read_only=True)
    local_amount = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()

    def get_local_amount(self, obj):
        return {"value": obj.local_amount, "currency": self.get_currency_code(obj)}

    def get_amount(self, obj):
        return {"value": obj.amount, "currency": self.get_currency_code(obj)}

    class Meta:
        model = Transaction
        fields = "__all__"


class TransactionWriteSerializer(serializers.ModelSerializer):
    """
    Write serializer for Transaction — accepts FK ids only.
    """

    class Meta:
        model = Transaction
        fields = [
            "id",
            "period",
            "account",
            "currency",
            "amount",
            "local_amount",
            "description",
            "payment_date",
            "identifier",
            "upload",
        ]

    def validate_period(self, period):
        if period.closed:
            raise serializers.ValidationError("The selected period is closed and cannot be modified.")
        return period


# Keep backward-compatible alias
TransactionSerializer = TransactionWriteSerializer


class UploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Upload
        fields = "__all__"


class UploadStep1Serializer(serializers.ModelSerializer):
    class Meta:
        model = Upload
        fields = ["id", "file"]


class UploadStep1InputSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if not value.name.endswith(".csv"):
            raise serializers.ValidationError("File must be a CSV.")
        return value


class UploadStep2Serializer(serializers.Serializer):
    result = serializers.JSONField()
    upload_type = serializers.ChoiceField(choices=Upload.UploadType.choices)


class LoanReaderSerializer(CurrencyMixin, serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()
    monthly_payment = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()

    def get_amount(self, obj):
        return {"value": obj.amount, "currency": self.get_currency_code(obj)}

    def get_monthly_payment(self, obj):
        return {"value": obj.monthly_payment, "currency": self.get_currency_code(obj)}

    def get_percentage(self, obj):
        return obj.percentage

    def get_end_date(self, obj):
        return obj.end_date.isoformat() if obj.end_date else None

    class Meta:
        model = Loan
        fields = "__all__"


class LoanWriterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = "__all__"


class SubscriptionReaderSerializer(CurrencyMixin, serializers.ModelSerializer):
    monthly_payment = serializers.SerializerMethodField()

    def get_monthly_payment(self, obj):
        return {"value": obj.monthly_payment, "currency": self.get_currency_code(obj)}

    class Meta:
        model = Subscription
        fields = "__all__"


class SubscriptionWriterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = "__all__"


# Keep backward-compatible alias
SubscriptionWriteSerializer = SubscriptionWriterSerializer
