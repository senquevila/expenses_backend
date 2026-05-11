from django.db.models import Sum

from expenses.models import Period, Transaction


def calculate_period_total(period: Period) -> None:
    result = Transaction.objects.filter(period=period).aggregate(total=Sum("local_amount"))
    period.total = result["total"] or 0
    period.save(update_fields=["total"])
