from django.core.management.base import BaseCommand
from bookingstack.models import OpenerMap
from bookingstack.views import get_object_or_404  # or import Venue directly if you prefer
from django.apps import apps
from django.conf import settings
from datetime import date

VENUE_MODEL_LABEL = getattr(settings, "VENUE_MODEL", "pages.Venue")
Venue = apps.get_model(VENUE_MODEL_LABEL)

class Command(BaseCommand):
    help = "Scrape recent lineups per venue and populate OpenerMap (stub)."

    def handle(self, *args, **kwargs):
        for v in Venue.objects.all()[:50]:
            # TODO: Real scraping of the venue’s events page / FB Events / Bandsintown.
            # Stub: add 2 pretend artists so you can test UI.
            for name in [f"{v.name} Local Opener A", f"{v.name} Local Opener B"]:
                OpenerMap.objects.update_or_create(
                    venue=v, artist_name=name,
                    defaults={"contact_url": "", "last_seen": date.today()}
                )
            self.stdout.write(self.style.SUCCESS(f"Populated openers for {v.name} (stub)."))
