from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from django.contrib.auth import get_user_model
import re
from django.core.exceptions import ValidationError

User = get_user_model()

# Create your models here.
class Show(models.Model):
    date = models.DateTimeField()
    venue_name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    tickets_url = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.venue_name} — {self.city}, {self.state} — {self.date:%Y-%m-%d}"

class Release(models.Model):
    TYPE_CHOICES = [
        ("album", "Album"),
        ("ep", "EP"),
        ("single", "Single"),
    ]
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    release_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    release_date = models.DateField()
    cover = models.ImageField(upload_to="releases/", blank=True, null=True)
    cover_url = models.URLField(blank=True)         # swap to ImageField later if you wish
    description = models.TextField(blank=True)
    links_url = models.URLField(blank=True, help_text="Smartlink/Linktree for this release")
    is_public = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["-release_date", "-id"]        # newest first

    def __str__(self):
        return self.title
    
    def clean(self):
        super().clean()
        if not self.cover and not self.cover_url:
            raise ValidationError("Upload a cover image or provide a cover URL.")
        if self.cover and self.cover_url:
            raise ValidationError("Use either an upload or a URL, not both.")
    
    def cover_src(self):
        # Prefer uploaded image; fallback to external URL
        if self.cover:
            return self.cover.url
        return self.cover_url or ""

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:220]
        super().save(*args, **kwargs)

    @property
    def type_label(self) -> str:
        return dict(self.TYPE_CHOICES).get(self.release_type, "").title()

class Track(models.Model):
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name="tracks")
    track_number = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200)
    duration_seconds = models.PositiveIntegerField(default=0)  # 0 if unknown

    class Meta:
        ordering = ["track_number", "id"]

    def __str__(self):
        return f"{self.title} ({self.release.title})"
    
class Video(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    youtube_url = models.URLField(help_text="Any YouTube link: watch?v=, youtu.be/, or share URL")
    published_at = models.DateField(null=True, blank=True)
    is_public = models.BooleanField(default=True)
    sort = models.PositiveIntegerField(default=0, help_text="Lower shows first (then newest)")

    class Meta:
        ordering = ["sort", "-published_at", "-id"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:220]
        super().save(*args, **kwargs)

    @property
    def youtube_id(self) -> str:
        """
        Robust-ish extractor for common formats:
        - https://www.youtube.com/watch?v=ID
        - https://youtu.be/ID
        - https://www.youtube.com/embed/ID
        """
        url = self.youtube_url or ""
        # watch?v=
        m = re.search(r"[?&]v=([A-Za-z0-9_-]{6,})", url)
        if m: return m.group(1)
        # youtu.be/
        m = re.search(r"youtu\.be/([A-Za-z0-9_-]{6,})", url)
        if m: return m.group(1)
        # embed/
        m = re.search(r"/embed/([A-Za-z0-9_-]{6,})", url)
        if m: return m.group(1)
        return ""

class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=120, blank=True)
    source = models.CharField(max_length=80, blank=True, help_text="Where they signed up (e.g., /email-signup)")
    consent = models.BooleanField(default=True)  # keep it simple; toggle if you need explicit checkbox
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)  # for double opt-in later

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

class Artist(models.Model):
    ROLE_CHOICES = [("headliner","Headliner"),("opener","Opener"),("guest","Guest")]
    # Ownership
    user = models.OneToOneField(
        User, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        help_text="Headliner account that can edit this EPK.",
        related_name="artist_dashboard"
    )
    # Public info
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    short_tag = models.CharField(max_length=40, blank=True, help_text="Short label used on the headliners grid")
    genre = models.CharField(max_length=120, blank=True)
    hometown = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="artists/avatar/", blank=True)
    hero_image = models.ImageField(upload_to="artists/hero/", blank=True)
    is_public = models.BooleanField(default=True)
    sort = models.PositiveIntegerField(default=0)
    default_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="opener")

    # socials / links
    website_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    spotify_url = models.URLField(blank=True)
    apple_url = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)

    class Meta:
        ordering = ["sort", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:180]
        super().save(*args, **kwargs)

class ArtistPhoto(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="artists/photos/")
    caption = models.CharField(max_length=200, blank=True)
    sort = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]

class ArtistVideo(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="videos")
    url = models.URLField(help_text="YouTube or Vimeo URL")
    title = models.CharField(max_length=200, blank=True)
    sort = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]

    @property
    def embed_src(self) -> str:
        u = self.url
        # YouTube watch?v or youtu.be
        m = re.search(r"[?&]v=([A-Za-z0-9_-]{6,})", u) or re.search(r"youtu\.be/([A-Za-z0-9_-]{6,})", u)
        if m:
            return f"https://www.youtube-nocookie.com/embed/{m.group(1)}"
        # Vimeo
        m = re.search(r"vimeo\.com/(?:video/)?(\d+)", u)
        if m:
            return f"https://player.vimeo.com/video/{m.group(1)}"
        # Fallback: open URL
        return ""

class MediaAlbum(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    show = models.ForeignKey("pages.Show", null=True, blank=True, on_delete=models.SET_NULL, related_name="media_albums")
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=10, blank=True)
    date = models.DateField(null=True, blank=True)
    is_public = models.BooleanField(default=True)
    sort = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort", "-date", "-id"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:220]
        # default city/state/date from show if present
        if self.show:
            self.city = self.city or self.show.city
            self.state = self.state or self.show.state
            self.date = self.date or self.show.date.date() if hasattr(self.show.date, "date") else self.show.date
        super().save(*args, **kwargs)

class MediaItem(models.Model):
    KIND_CHOICES = [("photo","Photo"), ("video","Video")]
    album = models.ForeignKey(MediaAlbum, on_delete=models.CASCADE, related_name="items")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default="photo")
    image = models.ImageField(upload_to="media/album/", blank=True)  # for photos
    caption = models.CharField(max_length=200, blank=True)
    url = models.URLField(blank=True, help_text="YouTube or Vimeo URL (for videos)")
    sort = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]

    def __str__(self):
        return f"{self.kind}: {self.caption or self.album.title}"

    @property
    def embed_src(self) -> str:
        u = self.url or ""
        m = re.search(r"[?&]v=([A-Za-z0-9_-]{6,})", u) or re.search(r"youtu\.be/([A-Za-z0-9_-]{6,})", u)
        if m: return f"https://www.youtube-nocookie.com/embed/{m.group(1)}"
        m = re.search(r"vimeo\.com/(?:video/)?(\d+)", u)
        if m: return f"https://player.vimeo.com/video/{m.group(1)}"
        return ""
    
class Badge(models.Model):
    """A badge type (tour-wide or milestone)."""
    slug = models.SlugField(max_length=120, unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=240, blank=True)
    icon = models.ImageField(upload_to="passport/badges/", blank=True)  # optional; or use emoji below
    emoji = models.CharField(max_length=8, blank=True, help_text="Fallback icon, e.g. 🌙")
    color = models.CharField(max_length=16, default="#7c5cff")  # accent color
    points = models.PositiveIntegerField(default=10)
    is_milestone = models.BooleanField(default=False)
    milestone_threshold = models.PositiveIntegerField(null=True, blank=True, help_text="Award when user has this many show badges")

    def __str__(self): return self.name

class ShowBadge(models.Model):
    """Connect a specific show to a badge, with a redeem code."""
    show = models.ForeignKey("pages.Show", on_delete=models.CASCADE, related_name="passport_badges")
    badge = models.ForeignKey(Badge, on_delete=models.PROTECT, related_name="show_links")
    code = models.CharField(max_length=40, unique=True, help_text="Redeem code (case-insensitive).")
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.badge.name} @ {self.show.venue_name} ({self.show.city})"

class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="earned_badges")
    badge = models.ForeignKey(Badge, on_delete=models.PROTECT, related_name="earners")
    show = models.ForeignKey("pages.Show", null=True, blank=True, on_delete=models.SET_NULL)  # set for per-show badges
    source = models.CharField(max_length=20, default="code")  # code, milestone, admin
    acquired_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "badge", "show")]  # same badge can exist across different shows

