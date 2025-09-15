# bookingstack/signals.py
from django.conf import settings
from django.apps import apps
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import VenueProfile

VENUE_MODEL_LABEL = getattr(settings, "VENUE_MODEL", "events.Venue")
Venue = apps.get_model(VENUE_MODEL_LABEL)

@receiver(post_save, sender=Venue)
def ensure_profile(sender, instance, created, **kwargs):
    # create or get the profile; safe for both created & updates
    VenueProfile.objects.get_or_create(venue=instance)
