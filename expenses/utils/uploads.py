import hashlib
import json
import re

from django.conf import settings
from django.db.models import Max, Min

from expenses.models import Account, Currency, Period, Transaction, Upload
from expenses.serializers import TransactionSerializer
from expenses.utils.tools import change_account_from_assoc, str_to_date

DATE_FIELD = 0
DESCRIPTION_FIELD = 1
# Credit card fields
AMOUNT_FIELD = 2
AMOUNT_CURRENCY_FIELD = 3
ACCOUNT_FIELD = 3
# Account fields
AMOUNT_DEBIT_FIELD = 2
AMOUNT_CREDIT_FIELD = 3


def process_credit_card_csv(upload: Upload):
    context = {"result": {}}
    created = 0

    # get default values
    defaults = get_defaults()

    # get the upload metadata
    row_range = upload.parameters["rows"]
    indexes = get_field_indexes_credit_card(upload.parameters["cols"])

    dates_set = set()

    for row in upload.data[row_range["start"] : row_range["end"] + 1]:
        row = [str(item).strip() for item in row]

        if skip_row_credit_card(row, indexes):
            continue

        message = {
            "data": context,
            "line_number": row[0],
            "source": row,
        }

        # create identifier
        row_hash = hashlib.sha256("".join(row[1:]).encode()).hexdigest()

        # check if the transaction already exists
        if Transaction.objects.filter(identifier=row_hash).exists():
            message["description"] = "Transaction already exists"
            set_message(**message)
            continue

        try:
            payment_date, period = get_payment_date_and_period(row, indexes)
            dates_set.add(payment_date)
        except ValueError as e:
            set_message(
                description=str(e),
                line_number=row[0],
                source=row,
                data=context,
            )
            continue

        if not period or period.closed:
            set_message(
                description="Period not found or closed",
                line_number=row[0],
                source=row,
                data=context,
            )
            continue

        # get the amount and local currency
        amount, currency = get_transaction_money_credit_card(row, indexes, defaults["currency"])

        if not amount:
            message["description"] = "Amount zero"
            set_message(**message)
            continue

        description = row[indexes["description"]]

        # TODO: temporal
        if Transaction.objects.filter(
            period=period,
            currency=currency,
            description=description,
            amount=amount,
            payment_date=payment_date,
        ).exists():
            message["description"] = "Transaction already exists"
            set_message(**message)
            continue

        if amount > 0:
            default_account = defaults["expense_account"]
        else:
            default_account = defaults["income_account"]

        serializer = TransactionSerializer(
            data={
                "payment_date": payment_date,
                "description": description,
                "period": period.pk,
                "account": default_account.pk,
                "currency": currency.pk,
                "amount": abs(amount),
                "upload": upload.pk,
                "identifier": row_hash,
            }
        )
        if serializer.is_valid():
            serializer.save()
            created += 1
            message["description"] = "CREATED"
        else:
            message["description"] = str(serializer.errors)
        set_message(**message)

    context["summary"] = {
        "created": created,
        "total": upload.parameters["rows"]["end"] - upload.parameters["rows"]["start"],
    }

    # change the account from the association
    change_account_from_assoc()

    upload.result = json.dumps(context)
    upload.start_date = min(dates_set) if dates_set else None
    upload.end_date = max(dates_set) if dates_set else None
    upload.save()
    update_interval_date(upload)


def process_account_csv(upload: Upload, currency: Currency):
    context = {"result": {}}
    created = 0

    # get default values
    defaults = get_defaults()

    # get the upload metadata
    row_range = upload.parameters["rows"]
    indexes = get_field_indexes_account(upload.parameters["cols"])
    upload_currency = currency  # preserve to avoid rebinding inside the loop

    for row in upload.data[row_range["start"] : row_range["end"] + 1]:
        row = [str(item).strip() for item in row]

        if skip_row_account(row, indexes):
            continue

        message = {
            "data": context,
            "line_number": row[0],
            "source": row,
        }

        # create identifier
        row_hash = hashlib.sha256("".join(row[1:]).encode()).hexdigest()

        # check if the transaction already exists
        if Transaction.objects.filter(identifier=row_hash).exists():
            message["description"] = "Transaction already exists"
            set_message(**message)
            continue

        try:
            payment_date, period = get_payment_date_and_period(row, indexes)
        except ValueError as e:
            set_message(
                description=str(e),
                line_number=row[0],
                source=row,
                data=context,
            )
            continue

        if not period or period.closed:
            set_message(
                description="Period not found or closed",
                line_number=row[0],
                source=row,
                data=context,
            )
            continue

        # get the amount and local currency
        amount, currency, is_credit = get_transaction_money_account(row, indexes, upload_currency, defaults["currency"])

        if not amount:
            message["description"] = "Amount zero"
            set_message(**message)
            continue

        description = row[indexes["description"]]

        # TODO: temporal
        if Transaction.objects.filter(
            period=period,
            currency=currency,
            description=description,
            amount=amount,
            payment_date=payment_date,
        ).exists():
            message["description"] = "Transaction already exists"
            set_message(**message)
            continue

        account = defaults["income_account"] if is_credit else defaults["expense_account"]

        serializer = TransactionSerializer(
            data={
                "payment_date": payment_date,
                "description": description,
                "period": period.pk,
                "account": account.pk,
                "currency": currency.pk,
                "amount": amount,
                "upload": upload.pk,
                "identifier": row_hash,
            }
        )
        if serializer.is_valid():
            serializer.save()
            created += 1
            message["description"] = "CREATED"
        else:
            message["description"] = str(serializer.errors)
        set_message(**message)

    context["summary"] = {
        "created": created,
        "total": upload.parameters["rows"]["end"] - upload.parameters["rows"]["start"],
    }

    # change the account from the association
    change_account_from_assoc()

    upload.result = json.dumps(context)
    upload.save()
    update_interval_date(upload)


def get_defaults() -> dict:
    default_currency = Currency.objects.filter(alpha3=settings.DEFAULT_CURRENCY).first()
    if not default_currency:
        raise ValueError("Default currency not configured")

    default_expense_account = Account.objects.filter(name=settings.DEFAULT_EXPENSE_ACCOUNT).first()
    if not default_expense_account:
        raise ValueError("Default expense account not configured")

    default_income_account = Account.objects.filter(name=settings.DEFAULT_INCOME_ACCOUNT).first()
    if not default_income_account:
        raise ValueError("Default income account not configured")

    return {
        "currency": default_currency,
        "expense_account": default_expense_account,
        "income_account": default_income_account,
    }


def get_field_indexes_credit_card(cols):
    return {
        "payment_date": cols[DATE_FIELD]["payment_date"],
        "description": cols[DESCRIPTION_FIELD]["description"],
        "amount": cols[AMOUNT_FIELD]["amount"],
        "amount_currency": cols[AMOUNT_CURRENCY_FIELD]["amount_currency"],
    }


def get_field_indexes_account(cols):
    return {
        "payment_date": cols[DATE_FIELD]["payment_date"],
        "description": cols[DESCRIPTION_FIELD]["description"],
        "amount_debit": cols[AMOUNT_DEBIT_FIELD]["amount_debit"],
        "amount_credit": cols[AMOUNT_CREDIT_FIELD]["amount_credit"],
    }


def skip_row_credit_card(row: list, indexes: list) -> bool:
    try:
        return (
            not row
            or not row[indexes["payment_date"]]
            or (not row[indexes["amount"]] and not row[indexes["amount_currency"]])
        )
    except IndexError:
        return True


def skip_row_account(row: list, indexes: list) -> bool:
    try:
        return (
            not row
            or not row[indexes["payment_date"]]
            or (not row[indexes["amount_debit"]] and not row[indexes["amount_credit"]])
        )
    except IndexError:
        return True


def get_payment_date_and_period(row, indexes):
    payment_date = str_to_date(row[indexes["payment_date"]])
    period = Period.get_period_from_date(payment_date)
    return payment_date, period


def get_transaction_money_credit_card(row, indexes, default_currency):
    """
    Take two columns for amount and return the non-zero amount with its currency.

    :param row: CSV row data
    :param indexes: Indexes for amount and amount_currency
    :param default_currency: Default currency object
    :return: Tuple of (amount, currency)
    """

    amounts = [
        get_amount(row, indexes["amount"], default_currency),
        get_amount_currency(row, indexes["amount_currency"], default_currency),
    ]

    # Filter out None and zero values
    valid_amounts = [(amount, currency) for amount, currency in amounts if amount is not None and amount != 0]

    if valid_amounts:
        # Return the tuple with the non-zero amount
        return valid_amounts[0]
    else:
        return None, None


def get_transaction_money_account(row, indexes, currency, default_currency):
    if currency and currency.pk == default_currency.pk:
        amounts = [
            get_amount(row, indexes["amount_debit"], default_currency),
            get_amount(row, indexes["amount_credit"], default_currency),
        ]
    else:
        amounts = [
            get_amount_currency(row, indexes["amount_debit"], currency),
            get_amount_currency(row, indexes["amount_credit"], currency),
        ]

    # Tag each amount with its source index (0=debit, 1=credit), apply abs
    tagged = [
        (abs(amount), currency, idx)
        for idx, (amount, currency) in enumerate(amounts)
        if amount is not None
    ]

    if tagged:
        best = max(tagged, key=lambda x: x[0])
        is_credit = best[2] == 1
        return best[0], best[1], is_credit
    else:
        return None, None, None


def set_message(data: dict, line_number: int, source: str, description: str):
    if line_number not in data["result"]:
        data["result"][line_number] = {}

    data["result"][line_number] = {
        "source": str(source),
        "description": description,
    }


def get_amount(row: list, index: int, default_currency) -> tuple:
    """
    Asumming that the value is: [number currency]
    """
    # check if the index is valid
    if index < 0:
        return None, None

    try:
        value = str(row[index])
    except IndexError:
        return None, None

    # replace weird characters
    value = value.replace("\xa0", " ").replace(",", "")
    amount_str, currency_str = extract_currency_and_value(value)
    try:
        amount = float(amount_str)
    except (IndexError, ValueError, TypeError):
        amount = None

    if not amount:
        return None, None

    currency_str = currency_str or ""
    q_currency = Currency.objects.filter(alpha3=currency_str)
    if q_currency.exists():
        currency = q_currency.first()
    else:
        currency = default_currency

    return (float(amount), currency)


def get_amount_currency(row: list, index: int, default_currency) -> tuple:
    row[index] = "USD " + str(row[index])
    return get_amount(row, index, default_currency)


def extract_currency_and_value(input: str) -> tuple:
    # Updated pattern to handle negative amounts and currency symbol both before and after the value
    pattern = r"(?P<currency1>L|LPS|HNL|USD)?\s*(?P<value>-?\d+(?:\.\d{2})?)\s*(?P<currency2>L|LPS|HNL|USD)?"
    match = re.search(pattern, input)
    if match:
        value = match.group("value")
        # Check if currency1 is present, else fallback to currency2
        currency = match.group("currency1") or match.group("currency2")

        currency_map = {
            "L": "HNL",  # Assuming 'L' stands for Lempira, the currency of Honduras
            "LPS": "HNL",
            "HNL": "HNL",
            "USD": "USD",
        }

        return value, currency_map.get(currency, None)
    else:
        return None, None


def update_interval_date(upload: Upload):
    """
    Update the upload start_date and end_date with the min and max payment_date
    of transactions associated with the upload.
    """
    # Get min and max dates in a single query
    date_range = Transaction.objects.filter(upload=upload).aggregate(
        min_date=Min("payment_date"),
        max_date=Max("payment_date"),
    )

    # Only update if transactions exist
    if date_range["min_date"] and date_range["max_date"]:
        upload.start_date = date_range["min_date"]
        upload.end_date = date_range["max_date"]
        upload.save()
