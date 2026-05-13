import hashlib
import re

from django.conf import settings

from expenses.models import Account, AccountAssociation, Currency, Period, Transaction, Upload
from expenses.serializers import TransactionSerializer
from expenses.utils.tools import str_to_date


def _fail(upload: Upload, error: str):
    upload.fails = [{"error": error}]
    upload.upload_status = Upload.UploadStatus.FAILED
    upload.save(update_fields=["fails", "upload_status"])


def process_upload_result(upload: Upload):
    upload.upload_status = Upload.UploadStatus.PROCESSING
    upload.save(update_fields=["upload_status"])

    rows = upload.result
    if not rows:
        _fail(upload, "No result data to process")
        return

    upload_type = upload.upload_type
    if not upload_type:
        _fail(upload, "upload_type is not set")
        return

    detected_type = _detect_type_from_structure(rows[0])
    if detected_type != upload_type:
        _fail(upload, f"upload_type '{upload_type}' does not match result structure (detected '{detected_type}')")
        return

    defaults = _get_defaults()
    associations = list(AccountAssociation.objects.only("token", "account").select_related("account"))
    fails = []
    created = 0

    for row in rows:
        row_number = row.get("row_number")
        description = row.get("description", "")

        identifier = _make_identifier(row)
        if Transaction.objects.filter(identifier=identifier).exists():
            fails.append({"row_number": row_number, "description": description, "reason": "Duplicate transaction"})
            continue

        try:
            payment_date = str_to_date(row.get("date", ""))
        except ValueError as e:
            fails.append({"row_number": row_number, "description": description, "reason": str(e)})
            continue

        period = Period.get_period_from_date(payment_date)
        if not period or period.closed:
            fails.append({"row_number": row_number, "description": description, "reason": "Period not found or closed"})
            continue

        if upload_type == Upload.UploadType.CREDIT_CARD:
            amount, currency, is_income = _parse_credit_card_row(row, defaults["currency"])
        else:
            amount, currency, is_income = _parse_savings_account_row(row, defaults["currency"])

        if not amount:
            fails.append({"row_number": row_number, "description": description, "reason": "Amount is zero or invalid"})
            continue

        account = defaults["income_account"] if is_income else defaults["expense_account"]
        for assoc in associations:
            if assoc.token.lower() in description.lower():
                account = assoc.account
                break

        serializer = TransactionSerializer(
            data={
                "payment_date": payment_date,
                "description": description,
                "period": period.pk,
                "account": account.pk,
                "currency": currency.pk,
                "amount": abs(amount),
                "upload": upload.pk,
                "identifier": identifier,
            }
        )
        if serializer.is_valid():
            serializer.save()
            created += 1
        else:
            fails.append({"row_number": row_number, "description": description, "reason": str(serializer.errors)})

    _update_fields = []
    if fails:
        upload.fails = fails
        _update_fields.append("fails")

    upload.upload_status = Upload.UploadStatus.DONE
    _update_fields.append("upload_status")
    upload.save(update_fields=_update_fields)
    _update_interval_dates(upload, rows)


def _detect_type_from_structure(row: dict) -> str | None:
    if "local" in row and "usd" in row:
        return Upload.UploadType.CREDIT_CARD
    if "debit" in row and "credit" in row:
        return Upload.UploadType.SAVINGS_ACCOUNT
    return None


def _get_defaults() -> dict:
    default_currency = Currency.objects.filter(alpha3=settings.DEFAULT_CURRENCY).first()
    if not default_currency:
        raise ValueError("Default currency not configured")
    expense_account = Account.objects.filter(name=settings.DEFAULT_EXPENSE_ACCOUNT).first()
    if not expense_account:
        raise ValueError("Default expense account not configured")
    income_account = Account.objects.filter(name=settings.DEFAULT_INCOME_ACCOUNT).first()
    if not income_account:
        raise ValueError("Default income account not configured")
    return {
        "currency": default_currency,
        "expense_account": expense_account,
        "income_account": income_account,
    }


def _make_identifier(row: dict) -> str:
    fields = [row.get("date", ""), row.get("description", "")]
    for key in ("local", "usd", "debit", "credit"):
        if key in row:
            fields.append(str(row.get(key, {}).get("amount", "")))
    return hashlib.sha256("".join(fields).encode()).hexdigest()


def _parse_amount_field(field: dict, default_currency: Currency) -> tuple[float | None, Currency | None]:
    raw = field.get("amount", "")
    if not raw:
        return None, None
    try:
        amount = float(re.sub(r"[^\d.-]", "", str(raw).replace(",", "")))
    except (ValueError, AttributeError):
        return None, None
    if not amount:
        return None, None
    currency = Currency.objects.filter(alpha3=field.get("currency", "")).first() or default_currency
    return amount, currency


def _parse_credit_card_row(row: dict, default_currency: Currency) -> tuple[float | None, Currency | None, bool]:
    """Use local amount first, fall back to USD. Negative amount = income."""
    amount, currency = _parse_amount_field(row.get("local", {}), default_currency)
    if not amount:
        amount, currency = _parse_amount_field(row.get("usd", {}), default_currency)
    is_income = amount is not None and amount < 0
    return amount, currency, is_income


def _parse_savings_account_row(row: dict, default_currency: Currency) -> tuple[float | None, Currency | None, bool]:
    """Credit = income, debit = expense. Credit takes precedence if both present."""
    credit_amount, credit_currency = _parse_amount_field(row.get("credit", {}), default_currency)
    if credit_amount:
        return credit_amount, credit_currency, True
    debit_amount, debit_currency = _parse_amount_field(row.get("debit", {}), default_currency)
    if debit_amount:
        return debit_amount, debit_currency, False
    return None, None, False


def _update_interval_dates(upload: Upload, rows: list[dict]):
    dates = []
    for row in rows:
        try:
            dates.append(str_to_date(row.get("date", "")))
        except ValueError:
            pass
    if dates:
        upload.start_date = min(dates)
        upload.end_date = max(dates)
        upload.save(update_fields=["start_date", "end_date"])
