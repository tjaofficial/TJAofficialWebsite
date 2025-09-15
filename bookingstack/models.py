# bookingstack/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

VENUE_MODEL_LABEL = getattr(settings, "VENUE_MODEL", "events.Venue")  # <-- lazy string

class VenueProfile(models.Model):
    # NOTE: remove invalid FK arg `unique=False` (not a valid kw on FK)
    venue = models.OneToOneField('events.Venue', on_delete=models.CASCADE, related_name="booking_profile")

    booking_email = models.EmailField(blank=True)
    booking_name = models.CharField(max_length=160, blank=True)
    booking_phone = models.CharField(max_length=80, blank=True)
    genre_fit = models.CharField(max_length=160, blank=True)
    website_override = models.URLField(blank=True)
    last_lineup_scrape = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["venue"], name="ux_venueprofile_venue_one")
        ]
        verbose_name = "Venue Profile"
        verbose_name_plural = "Venue Profiles"

class VenueContact(models.Model):
    venue = models.ForeignKey('events.Venue', on_delete=models.CASCADE, related_name="booking_contacts")
    name = models.CharField(max_length=160, blank=True)
    role = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=80, blank=True)
    is_primary = models.BooleanField(default=False)

class Outreach(models.Model):
    EMAIL, CALL = "email", "call"
    KIND_CHOICES = [(EMAIL, "Email"), (CALL, "Call")]
    venue = models.ForeignKey(VENUE_MODEL_LABEL, on_delete=models.CASCADE, related_name="outreach")
    contact = models.ForeignKey("VenueContact", on_delete=models.SET_NULL, null=True, blank=True)
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, default=EMAIL)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    sent_at = models.DateTimeField(default=timezone.now)
    reply_received = models.BooleanField(default=False)
    next_followup_at = models.DateTimeField(null=True, blank=True)
    followup_notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

class ShowInquiry(models.Model):
    venue = models.ForeignKey(VENUE_MODEL_LABEL, on_delete=models.CASCADE, related_name="inquiries")
    target_start = models.DateField(null=True, blank=True)
    target_end = models.DateField(null=True, blank=True)
    hard_date = models.DateField(null=True, blank=True)
    expected_draw = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=40, default="pending")  # pending/hold/confirmed/declined
    hold_expires = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

class TechAsset(models.Model):
    STAGE_PLOT, TECH_RIDER, ADVANCE = "stage_plot", "tech_rider", "advance"
    KIND_CHOICES = [(STAGE_PLOT, "Stage Plot"), (TECH_RIDER, "Tech Rider"), (ADVANCE, "Advance")]
    kind = models.CharField(max_length=40, choices=KIND_CHOICES)
    file = models.FileField(upload_to="booking/assets/")
    created_at = models.DateTimeField(auto_now_add=True)

class EpkVisit(models.Model):
    venue = models.ForeignKey(VENUE_MODEL_LABEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="epk_visits")
    session_id = models.CharField(max_length=64)
    opened_at = models.DateTimeField(auto_now_add=True)
    referrer = models.CharField(max_length=256, blank=True)
    utm_source = models.CharField(max_length=80, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

class FanSupport(models.Model):
    venue = models.ForeignKey(VENUE_MODEL_LABEL, on_delete=models.CASCADE, related_name="fan_support")
    name = models.CharField(max_length=160)
    email = models.EmailField()
    postal_code = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class SocialMetricSnapshot(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    city = models.CharField(max_length=120, blank=True)
    metro_radius_km = models.PositiveIntegerField(default=80)
    spotify_monthly_listeners = models.IntegerField(null=True, blank=True)
    instagram_local_followers = models.IntegerField(null=True, blank=True)
    tiktok_local_followers = models.IntegerField(null=True, blank=True)

class OpenerMap(models.Model):
    venue = models.ForeignKey(VENUE_MODEL_LABEL, on_delete=models.CASCADE, related_name="opener_map")
    artist_name = models.CharField(max_length=160)
    contact_url = models.URLField(blank=True)     # IG, site, etc.
    last_seen = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["venue", "artist_name"])]



