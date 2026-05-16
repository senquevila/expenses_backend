import hashlib
from datetime import date
from decimal import Decimal
from typing import Union


def make_transaction_identifier(
    payment_date: date, description: str, amount: Union[Decimal, float, int], currency_alpha3: str
) -> str:
    """Canonical identifier for a transaction, derivable from stored fields."""
    d = Decimal(str(amount))
    fields = [
        str(payment_date),
        str(description or ""),
        f"{abs(d):.2f}",
        str(currency_alpha3 or ""),
    ]
    return hashlib.sha256("".join(fields).encode()).hexdigest()
