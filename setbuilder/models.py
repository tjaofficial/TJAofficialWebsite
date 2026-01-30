# setbuilder/models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.text import slugify

User = settings.AUTH_USER_MODEL

class Song(models.Model):
    GENRE_CHOICES = [
        ("hiphop","Hip-Hop"), ("rnb","R&B"), ("pop","Pop"),
        ("edm","EDM"), ("trap","Trap"), ("alt","Alt/Indie"),
        ("other","Other"),
    ]
    primary_artist = models.ForeignKey("pages.Artist", on_delete=models.CASCADE, related_name="songs")
    title = models.CharField(max_length=160)
    duration_seconds = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    is_collab = models.BooleanField(default=False)
    collab_kind = models.CharField(max_length=16, blank=True, choices=[("headliners","Headliners"), ("other","Other")])
    collaborator_artists = models.ManyToManyField("pages.Artist", blank=True, related_name="featured_on")
    collab_other = models.CharField(max_length=200, blank=True)  # free-text for non-headliner collabs
    genre = models.CharField(max_length=12, choices=GENRE_CHOICES, blank=True)
    feeling = models.CharField(max_length=200, blank=True)  # “short description of the feeling”
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["primary_artist__name", "title"]

    def __str__(self):
        return f"{self.primary_artist.name} — {self.title}"

    @property
    def duration_label(self):
        m, s = divmod(self.duration_seconds, 60)
        return f"{m}:{s:02d}"


class ShowSet(models.Model):
    VIBE_CHOICES = [("intimate","Intimate"), ("hype","Hype/Energetic"), ("mixed","Mixed")]
    label = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    vibe = models.CharField(max_length=12, choices=VIBE_CHOICES, default="mixed")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="showsets")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.label)[:180]
        return super().save(*args, **kwargs)

    def total_seconds(self):
        return sum(self.items.values_list("duration_seconds", flat=True))

    def total_label(self):
        m, s = divmod(self.total_seconds(), 60)
        return f"{m}:{s:02d}"

class ShowItem(models.Model):
    KIND_CHOICES = [
        ("OPENER","Opener"),
        ("HEADLINER","Headliner"),
        ("COLLAB","Collaboration"),
        ("BREAK","Break"),
        ("INTERMISSION","Intermission"),
        ("TALKING","Talking"),
    ]
    show = models.ForeignKey(ShowSet, on_delete=models.CASCADE, related_name="items")
    sort = models.PositiveIntegerField(default=0)
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    # References
    artist = models.ForeignKey("pages.Artist", null=True, blank=True, on_delete=models.SET_NULL)
    song = models.ForeignKey(Song, null=True, blank=True, on_delete=models.SET_NULL)
    # Display/Text
    display_name = models.CharField(max_length=200, blank=True)
    # Duration
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort","id"]
