from django.db import transaction
from django.db.models import Sum

from expenses.models import Period, Transaction


def calculate_period_total(period: Period) -> None:
    with transaction.atomic():
        locked_period = Period.objects.select_for_update().get(pk=period.pk)
        result = Transaction.objects.filter(period=locked_period).valid().aggregate(total=Sum("local_amount"))
        locked_period.total = result["total"] or 0
        locked_period.save(update_fields=["total"])
        period.total = locked_period.total
