from django.db import models
import uuid
from django.utils import timezone
from django.conf import settings

# Create your models here.
from django.db import models

class Venue(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=60, blank=True)
    state = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=60, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    owner_name = models.CharField(max_length=120, blank=True)
    owner_email = models.EmailField(blank=True)
    entertainment_manager = models.CharField(max_length=120, blank=True)
    entertainment_email = models.EmailField(blank=True)
    hours = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name

class Event(models.Model):
    name = models.CharField(max_length=200, blank=True)
    is_tour_stop = models.BooleanField(default=False)
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    venue = models.ForeignKey(Venue, null=True, blank=True, on_delete=models.SET_NULL)
    afterparty_info = models.TextField(blank=True)
    meet_greet_info = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="events/cover/", blank=True, null=True,
                                    help_text="Wide hero image for the Events page.")
    flyer       = models.ImageField(upload_to="events/flyer/", blank=True, null=True,
                                    help_text="Portrait flyer used on cards if no cover.")
    published = models.BooleanField(default=False)

    @property
    def hero_src(self):
        return (self.cover_image.url if self.cover_image
                else (self.flyer.url if self.flyer else ""))
    
    def __str__(self):
        return self.name or f"Event {self.pk}"
    
class TechPerson(models.Model):
    ROLE_CHOICES = [
        ("sound", "Sound"),
        ("lighting", "Lighting"),
        ("guitarist", "Guitarist"),
        ("drummer", "Drummer"),
        ("engineer", "Engineer"),
        ("stagehand", "Stagehand"),
        ("other", "Other"),
    ]
    name = models.CharField(max_length=160)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default="other")
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    rate_cents = models.PositiveIntegerField(default=0, help_text="Per-show rate in cents")
    notes = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} – {self.get_role_display()}"

class EventTechAssignment(models.Model):
    event = models.ForeignKey("Event", on_delete=models.CASCADE, related_name="tech_assignments")
    person = models.ForeignKey(TechPerson, on_delete=models.PROTECT, related_name="assignments")
    role = models.CharField(max_length=30, blank=True, help_text="Override role/title for this show")
    rate_cents = models.PositiveIntegerField(default=0)
    confirmed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [("event","person")]

    def __str__(self):
        return f"{self.event} — {self.person}"

class EventMedia(models.Model):
    KIND_CHOICES = [("image","Image"), ("video","Video")]
    event = models.ForeignKey("Event", on_delete=models.CASCADE, related_name="media")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default="image")
    image = models.ImageField(upload_to="event_media/", blank=True, null=True)
    video_url = models.URLField(blank=True, help_text="YouTube/Vimeo/etc.")
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.kind == "image" and not self.image:
            raise ValidationError("Upload an image for kind=image")
        if self.kind == "video" and not self.video_url:
            raise ValidationError("Provide a video_url for kind=video")

    def __str__(self):
        return f"{self.event} — {self.kind}"

class EventArtist(models.Model):
    ROLE_CHOICES = [
        ("headliner", "Headliner"),
        ("opener", "Opener"),
        ("guest", "Guest"),
    ]
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="artist_slots")
    artist = models.ForeignKey("pages.Artist", on_delete=models.PROTECT, related_name="event_slots")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="opener")
    set_order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("event", "artist")]
        ordering = ["set_order", "id"]

    def __str__(self):
        return f"{self.event} — {self.artist} ({self.role})"

class ArtistSaleLink(models.Model):
    """Unique sale link per (event, artist) for attribution + QR."""
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="artist_links")
    artist = models.ForeignKey("pages.Artist", on_delete=models.CASCADE, related_name="sale_links")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    enabled = models.BooleanField(default=True)
    note = models.CharField(max_length=120, blank=True)

    class Meta:
        unique_together = [("event", "artist")]

    def __str__(self):
        return f"{self.event} — {self.artist} link"

class ArtistLinkHit(models.Model):
    link = models.ForeignKey("events.ArtistSaleLink", on_delete=models.CASCADE, related_name="hits")
    at = models.DateTimeField(auto_now_add=True)
    user_agent = models.CharField(max_length=300, blank=True)
    referer = models.URLField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["link", "at"])]

class ChecklistTemplate(models.Model):
    name = models.CharField(max_length=120, default="Default Event Checklist")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class ChecklistTemplateItem(models.Model):
    template = models.ForeignKey(ChecklistTemplate, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title

# A concrete checklist attached to one Event
class EventChecklist(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="checklist")
    created_at = models.DateTimeField(auto_now_add=True)
    template_used = models.ForeignKey(ChecklistTemplate, null=True, blank=True, on_delete=models.SET_NULL)

    def progress(self):
        total = self.items.count()
        done = self.items.filter(done_at__isnull=False).count()
        return (done, total)

    def __str__(self):
        return f"{self.event} Checklist"

class EventChecklistItem(models.Model):
    checklist = models.ForeignKey(EventChecklist, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    # workflow
    done_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    # optional planning helpers
    is_required = models.BooleanField(default=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_check_items"
    )
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["order", "id"]
        indexes = [models.Index(fields=["checklist", "order"])]

    @property
    def is_done(self):
        return self.done_at is not None

    def toggle(self, user=None):
        if self.done_at:
            self.done_at = None
            self.completed_by = None
        else:
            self.done_at = timezone.now()
            if user and user.is_authenticated:
                self.completed_by = user
        self.save(update_fields=["done_at", "completed_by"])