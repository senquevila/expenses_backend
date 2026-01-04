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


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for the Transaction model.
    """

    class Meta:
        model = Transaction
        fields = "__all__"


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
