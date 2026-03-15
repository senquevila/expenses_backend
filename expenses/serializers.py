from rest_framework import serializers

from expenses.models import (
    Account,
    AccountAsociation,
    CurrencyConvert,
    Loan,
    Period,
    Subscription,
    Transaction,
    Upload,
)


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = "__all__"
        ordering = ["account_type", "name"]


class AccountAssociationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountAsociation
        fields = "__all__"
        ordering = ["account__name"]


class CurrencyConvertSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyConvert
        fields = "__all__"


class PeriodSerializer(serializers.ModelSerializer):
    """
    Serializer for the Period model.
    """

    class Meta:
        model = Period
        fields = "__all__"
        ordering = ["-year", "-month"]


class TransactionReadSerializer(serializers.ModelSerializer):
    """
    Read serializer for Transaction — expands all related objects.
    """

    period = PeriodSerializer(read_only=True)
    account = AccountSerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = "__all__"


class TransactionWriteSerializer(serializers.ModelSerializer):
    """
    Write serializer for Transaction — accepts FK ids only.
    """

    class Meta:
        model = Transaction
        fields = ["id", "period", "account", "currency", "amount", "description", "payment_date", "identifier", "upload"]

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


class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = "__all__"


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = "__all__"
