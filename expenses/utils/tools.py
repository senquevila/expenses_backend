from datetime import datetime
from decimal import Decimal
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from django.conf import settings
from django.db.models import F, Sum
from django.db.models.functions import Abs
from rest_framework import status

from expenses.models import AccountAssociation, Currency, CurrencyConvert, Transaction

DOLAR_CODE = "USD"


def get_real_amount(expense: Transaction) -> float:
    data = (
        CurrencyConvert.objects.filter(currency=expense.currency)
        .annotate(date_diff=Abs(F("date") - expense.payment_date))
        .order_by("date_diff")[:1]
    )
    return expense.account.sign * expense.amount * data.first().exchange


def str_to_date(str_date) -> datetime.date:
    valid_formats = ["%Y-%m-%d", "%d/%m/%y", "%d/%m/%Y", "%d-%m-%Y", "%d-%m-%y"]

    for format in valid_formats:
        try:
            return datetime.strptime(str_date, format).date()
        except ValueError:
            continue

    raise ValueError(f"Invalid date format: {str_date}")


def get_total_local_amount(filtered) -> Decimal:
    queryset = (
        Transaction.objects.filter(filtered)
        .exclude(account__name=settings.INVALID_ACCOUNT)
        .aggregate(total=Sum("local_amount"))
    )
    return queryset["total"] or 0


def change_account_from_assoc() -> list[dict]:
    """
    Update account associations in transactions based on matching tokens
    and return a summary of changes.
    """
    data = []

    # Retrieve only the necessary fields from AccountAssociation
    associations = AccountAssociation.objects.only("token", "account")

    for association in associations:
        transactions = Transaction.objects.filter(
            description__icontains=association.token, period__active=True
        ).exclude(account=association.account)

        # Prepare summary data and update transactions
        for transaction in transactions:
            data.append(
                {
                    "id": transaction.id,
                    "account_found": association.account.name,
                    "account_original": transaction.account.name,
                }
            )
            # Update the transaction's account
            transaction.account = association.account
            transaction.save(update_fields=["account"])

    return data


def remove_invalid_transactions() -> int:
    invalid_expenses = Transaction.objects.filter(account__name=settings.INVALID_ACCOUNT)
    rows, _ = invalid_expenses.delete()
    return rows


def create_dollar_conversion() -> tuple:
    def _get_exchange() -> float:
        req = Request(settings.SCRAPING_URL, headers={"User-Agent": "Mozilla/5.0"})
        page = urlopen(req)
        soup = BeautifulSoup(page, "html.parser")
        result = soup.find(id=settings.SCRAPING_TAG_ID)
        result_text = result.text.strip()
        tokens = result_text.split(settings.SCRAPING_TOKEN_SPLIT)
        value = float(tokens[-1].strip().replace("L", ""))
        return value

    if not CurrencyConvert.objects.filter(date=datetime.today()).exists():
        try:
            exchange = _get_exchange()
        except Exception as e:
            print(f"Error capturing exchange: {e}")
            return {"message": "Problem capturing exchange"}, status.HTTP_424_FAILED_DEPENDENCY

        currency = Currency.objects.filter(alpha3=DOLAR_CODE).first()

        CurrencyConvert.objects.create(currency=currency, exchange=exchange)

        return {"message": "Exchange created"}, status.HTTP_201_CREATED

    return {"message": "Exchange already exists"}, status.HTTP_204_NO_CONTENT
