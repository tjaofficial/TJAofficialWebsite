from django.core.management.base import BaseCommand
from events.models import Venue
from bookingstack.models import VenueProfile
import datetime

class Command(BaseCommand):
    help = "Scrape each venue’s public events page and cache recent lineups (stub)."

    def handle(self, *args, **kwargs):
        for v in Venue.objects.all():
            # TODO: implement site-specific scraper (or use a plugin system per venue)
            # set v.booking_profile.last_lineup_scrape
            profile, _ = VenueProfile.objects.get_or_create(venue=v)
            profile.last_lineup_scrape = datetime.datetime.utcnow()
            profile.save()
        self.stdout.write(self.style.SUCCESS("Scrape complete (stub)."))
