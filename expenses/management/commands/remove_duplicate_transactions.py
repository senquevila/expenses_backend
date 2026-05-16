from django.core.management.base import BaseCommand
from django.db.models import Count, Min

from expenses.models import Transaction


class Command(BaseCommand):
    help = "Find duplicate transactions and delete all but the oldest one"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        groups = (
            Transaction.objects.values("payment_date", "description", "amount", "currency")
            .annotate(count=Count("id"), keep_id=Min("id"))
            .filter(count__gt=1)
        )

        if not groups.exists():
            self.stdout.write("No duplicate transactions found.")
            return

        total_deleted = 0

        for group in groups:
            duplicates = Transaction.objects.filter(
                payment_date=group["payment_date"],
                description=group["description"],
                amount=group["amount"],
                currency=group["currency"],
            ).exclude(id=group["keep_id"])

            count = duplicates.count()
            self.stdout.write(
                f"{'[DRY RUN] ' if dry_run else ''}"
                f"Removing {count} duplicate(s): "
                f"{group['payment_date']} | {group['description']} | {group['amount']}"
            )

            if not dry_run:
                duplicates.delete()

            total_deleted += count

        action = "Would remove" if dry_run else "Removed"
        self.stdout.write(f"{action} {total_deleted} duplicate transaction(s).")
