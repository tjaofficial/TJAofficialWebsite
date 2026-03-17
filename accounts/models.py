from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
from django.utils import timezone
from events.models import Event

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    must_reset_password = models.BooleanField(default=True)  # force reset on first login

    def __str__(self):
        return f"Profile<{self.user.username}>"

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

class NfcHunt(models.Model):
    event_name = models.ForeignKey(Event, null=True, blank=True, on_delete=models.SET_NULL)
    slug = models.SlugField(unique=True)

    is_active = models.BooleanField(default=True)

    required_locations = models.PositiveIntegerField(default=4)

    """
    Example locations_json:
    [
        {"key": "merch", "path": "merch", "label": "Merch Table"},
        {"key": "stage", "path": "stage", "label": "Stage"},
        {"key": "lounge", "path": "lounge", "label": "Bar / Lounge"},
        {"key": "hidden", "path": "hidden", "label": "Hidden Spot"}
    ]
    """
    locations_json = models.JSONField(default=list, blank=True)

    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)

    completion_message = models.TextField(blank=True, null=True)
    reward_label = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_name} ({self.slug})"

    def is_currently_active(self):
        now = timezone.now()

        if not self.is_active:
            return False
        if self.start_at and now < self.start_at:
            return False
        if self.end_at and now > self.end_at:
            return False
        return True

    def get_location_keys(self):
        keys = []
        for item in self.locations_json or []:
            key = item.get("key")
            if key:
                keys.append(key)
        return keys

    def get_location_config(self, location_key):
        for item in self.locations_json or []:
            if item.get("key") == location_key:
                return item
        return None

    def get_required_count(self):
        """
        Use explicit required_locations if set,
        otherwise fall back to number of configured locations.
        """
        if self.required_locations:
            return self.required_locations
        return len(self.get_location_keys())


class NfcHuntEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="nfc_hunt_entries",
    )
    hunt = models.ForeignKey(
        NfcHunt,
        on_delete=models.CASCADE,
        related_name="entries",
    )

    """
    Example progress_json:
    {
        "merch": {"found": True, "found_at": "2026-03-16T20:14:00Z"},
        "stage": {"found": False, "found_at": None},
        "lounge": {"found": True, "found_at": "2026-03-16T20:20:00Z"},
        "hidden": {"found": False, "found_at": None}
    }
    """
    progress_json = models.JSONField(default=dict, blank=True)

    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    qr_token = models.CharField(max_length=128, unique=True, null=True, blank=True)
    qr_generated_at = models.DateTimeField(null=True, blank=True)

    redeemed = models.BooleanField(default=False)
    redeemed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "hunt")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.hunt.event_name}"

    def initialize_progress(self, save=True):
        """
        Ensure all hunt locations exist in progress_json.
        """
        changed = False
        progress = self.progress_json or {}

        for key in self.hunt.get_location_keys():
            if key not in progress:
                progress[key] = {
                    "found": False,
                    "found_at": None,
                }
                changed = True

        if changed:
            self.progress_json = progress
            if save:
                self.save(update_fields=["progress_json", "updated_at"])

        return self.progress_json

    def mark_location_found(self, location_key, save=True):
        self.initialize_progress(save=False)

        progress = self.progress_json or {}
        location_data = progress.get(location_key, {
            "found": False,
            "found_at": None,
        })

        if not location_data.get("found"):
            location_data["found"] = True
            location_data["found_at"] = timezone.now().isoformat()
            progress[location_key] = location_data
            self.progress_json = progress

        self.update_completion(save=False)

        if save:
            self.save()

    def get_found_count(self):
        progress = self.progress_json or {}
        return sum(1 for value in progress.values() if value.get("found") is True)

    def is_complete(self):
        return self.get_found_count() >= self.hunt.get_required_count()

    def update_completion(self, save=True):
        now = timezone.now()
        is_now_complete = self.is_complete()

        if is_now_complete and not self.completed:
            self.completed = True
            self.completed_at = now

            if not self.qr_token:
                self.qr_token = uuid.uuid4().hex
                self.qr_generated_at = now

        if save:
            self.save()

    def get_progress_percent(self):
        required = self.hunt.get_required_count()
        if required == 0:
            return 0
        return int((self.get_found_count() / required) * 100)
