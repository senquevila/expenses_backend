from django.core.management.base import BaseCommand

from expenses.models import Transaction
from expenses.utils.identifier import make_transaction_identifier


class Command(BaseCommand):
    help = "Recalculate transaction identifiers to a uniform canonical hash"

    def handle(self, *args, **options):
        transactions = Transaction.objects.select_related("currency")
        total = transactions.count()
        updated = 0
        skipped = 0

        for tx in transactions:
            if not tx.payment_date or not tx.amount or not tx.currency:
                skipped += 1
                continue

            new_identifier = make_transaction_identifier(
                tx.payment_date,
                tx.description,
                tx.amount,
                tx.currency.alpha3,
            )

            if tx.identifier != new_identifier:
                tx.identifier = new_identifier
                tx.save(update_fields=["identifier"])
                updated += 1

        self.stdout.write(f"Total: {total} | Updated: {updated} | Skipped: {skipped}")
