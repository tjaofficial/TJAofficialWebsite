# bookingstack/management/commands/backfill_venue_profiles.py
from django.core.management.base import BaseCommand
from django.apps import apps
from django.conf import settings
from bookingstack.models import VenueProfile

class Command(BaseCommand):
    help = "Create a 1:1 VenueProfile for each Venue; dedupe older FK rows."

    def handle(self, *args, **kwargs):
        Venue = apps.get_model(getattr(settings, "VENUE_MODEL", "events.Venue"))
        created_count = 0
        fixed_dupes = 0

        for v in Venue.objects.all():
            profiles = VenueProfile.objects.filter(venue=v).order_by("id")
            if not profiles.exists():
                VenueProfile.objects.create(venue=v)
                created_count += 1
            elif profiles.count() > 1:
                # keep the first, delete the rest
                keep = profiles.first()
                to_delete = profiles.exclude(id=keep.id)
                fixed_dupes += to_delete.count()
                to_delete.delete()

        self.stdout.write(self.style.SUCCESS(
            f"Backfill complete. Created: {created_count}, Duplicates removed: {fixed_dupes}"
        ))
