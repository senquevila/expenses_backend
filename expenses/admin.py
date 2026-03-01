from django.contrib import admin, messages
from django.db.models import Count
from django.utils import timezone

from expenses.models import (
    Account,
    AccountAsociation,
    Currency,
    CurrencyConvert,
    Loan,
    Period,
    ProgramTransaction,
    Subscription,
    Transaction,
    Upload,
)
from expenses.utils.tools import change_account_from_assoc, remove_invalid_transactions


def disabled_periods(PeriodAdmin, request, queryset):
    queryset.update(active=False)
    updates = queryset.count()
    messages.success(request=request, message=f"Disabled {updates} periods")


disabled_periods.short_description = "Disabled selected periods"


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = (
        "year",
        "month",
        "active",
    )
    list_filter = ("active",)
    ordering = [
        "-year",
        "-month",
    ]
    actions = [disabled_periods]


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    pass


@admin.register(CurrencyConvert)
class CurrencyConvertAdmin(admin.ModelAdmin):
    list_display = ("currency", "exchange", "date")
    list_filter = ("date", "currency")
    ordering = ["-date"]


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    ordering = ["name", "account_type"]


def remove_invalid_expenses(TransactionAdmin, request, queryset):
    deletes = remove_invalid_transactions()
    messages.success(request=request, message=f"Removed {deletes} invalid expenses")


remove_invalid_expenses.short_description = "Removed all the invalid expenses"


def assoc_default_account(TransactionAdmin, request, queryset):
    changes = change_account_from_assoc()
    messages.success(
        request=request,
        message=f"Associated {len(changes)} expenses with Default account",
    )


assoc_default_account.short_description = "Associate expenses from default account"


def update_local_amount(TransactionAdmin, request, queryset):
    changes = 0
    for transaction in queryset.all():
        print("Transaction info:", transaction.__dict__)
        _new_local_amount = transaction.get_local_amount
        print("New local amount:", _new_local_amount)
        if transaction.local_amount != _new_local_amount:
            changes += 1
            transaction.local_amount = _new_local_amount
            transaction.save()
    messages.success(request=request, message=f"{changes} transactions updated with new local amount")


update_local_amount.short_description = "Update transactions with new local amount"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "period",
        "description",
        "currency",
        "amount",
        "local_amount",
        "account_name",
        "payment_date",
        "upload",
        "created",
    )
    list_filter = (
        "period",
        "created",
        "currency",
        "account",
        "upload",
    )
    ordering = (
        "-payment_date",
        "-created",
    )
    search_fields = (
        "description__icontains",
        "account__name__icontains",
        "amount",
        "upload__file",
    )
    actions = [remove_invalid_expenses, assoc_default_account, update_local_amount]

    def account_name(self, obj):
        return obj.account.name

    account_name.short_description = "Account Name"


@admin.register(AccountAsociation)
class AccountAsociationAdmin(admin.ModelAdmin):
    search_fields = (
        "account__name__icontains",
        "token__icontains",
    )
    ordering = (
        "account__name",
        "token",
    )


def remove_empty_uploads(UploadAdmin, request, queryset):
    unused_uploads = Upload.objects.annotate(num_expenses=Count("transaction")).filter(num_expenses=0)
    deletes = unused_uploads.count()
    unused_uploads.delete()
    messages.success(request=request, message=f"Removed {deletes} uploads")


remove_empty_uploads.short_description = "Remove uploads with no transactions"


@admin.register(Upload)
class UploadAdmin(admin.ModelAdmin):
    list_display = ("file", "start_date", "end_date")
    actions = [remove_empty_uploads]
    ordering = ("-created",)


@admin.register(ProgramTransaction)
class ProgramTransactionAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "active")


def disable_completed_loans(LoanAdmin, request, queryset):
    loans = Loan.objects.filter(is_active=True)
    now = timezone.now().date()
    completed = []
    for loan in loans:
        if loan.end_date < now:
            completed.append(loan.pk)
    completed_loans = Loan.objects.filter(id__in=completed)
    updates = completed_loans.count()
    completed_loans.update(is_active=False)
    messages.success(request=request, message=f"Disabled {updates} completed loans")


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        "description",
        "start_date",
        "end_date",
        "months",
        "monthly_payment",
        "bank",
        "percentage",
        "is_active",
    )
    list_filter = ("is_active", "bank")
    ordering = ["bank", "-months"]
    actions = [disable_completed_loans]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("name", "subscription_type", "monthly_payment", "is_active")
    list_filter = ("is_active", "subscription_type")
    ordering = ["subscription_type", "monthly_payment"]
