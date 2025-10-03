from __future__ import annotations
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.apps import apps
from datetime import timedelta

class Command(BaseCommand):
    help = "Delete old, unfulfilled, expired ticket reservations."

    def add_arguments(self, parser):
        parser.add_argument("--older-than-min", type=int, default=24*60,
                            help="Only purge if expired more than this many minutes ago (default: 24h).")
        parser.add_argument("--limit", type=int, default=2000, help="Max rows per run.")
        parser.add_argument("--dry-run", action="store_true", help="Log only; no deletes.")

    def handle(self, *args, **opts):
        TicketReservation = apps.get_model("tickets", "TicketReservation")
        older_than_min = opts["older_than_min"]
        limit = opts["limit"]
        dry = opts["dry_run"]

        cutoff = timezone.now() - timedelta(minutes=older_than_min)
        qs = (TicketReservation.objects
              .filter(fulfilled=False, expires_at__lt=cutoff)
              .order_by("expires_at")[:limit])

        count = qs.count()
        if dry:
            self.stdout.write(self.style.WARNING(f"[dry-run] Would purge {count} rows"))
            return

        deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Purged {deleted} expired reservation rows"))
