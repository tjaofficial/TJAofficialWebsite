from django.core.management.base import BaseCommand
from django.utils import timezone
from bookingstack.models import Outreach

class Command(BaseCommand):
    help = "List due follow-ups (wire to email/SMS later)."

    def handle(self, *args, **kwargs):
        now = timezone.now()
        due = Outreach.objects.filter(reply_received=False, next_followup_at__lte=now)
        for o in due:
            self.stdout.write(f"[FOLLOW-UP] {o.venue} — {o.kind} sent {o.sent_at}, due {o.next_followup_at}")
        self.stdout.write(self.style.SUCCESS(f"{due.count()} follow-ups due."))
