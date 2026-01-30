# pages/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify

from events.models import Event
from .models import MediaItem, MediaAlbum

@receiver(post_save, sender=MediaItem)
def _set_cover_if_missing(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.kind == "photo" and instance.image and instance.album.cover_item_id is None:
        instance.album.cover_item = instance
        instance.album.save(update_fields=["cover_item"])


@receiver(post_save, sender=Event)
def ensure_album_for_event(sender, instance: Event, created: bool, **kwargs):
    if not created:
        return

    city  = (instance.venue.city if instance.venue else "") or ""
    state = (instance.venue.state if instance.venue else "") or ""
    date  = instance.start.date() if instance.start else None

    # Title shown on the media cards
    pretty_date = date.strftime("%b %d, %Y") if date else "Undated"
    title = f"{city}, {state} — {pretty_date}".strip(" ,—")

    # Slug needs to be unique + stable
    base = f"{city}-{state}-{date.isoformat() if date else 'undated'}-{instance.id}"
    slug = slugify(base)[:220] or f"event-{instance.id}"

    MediaAlbum.objects.create(
        title=title or (instance.name or f"Event {instance.id}"),
        slug=slug,
        show=instance,
        city=city,
        state=state,
        date=date,
        is_public=True,  # or False if you want them hidden until you upload media
        sort=0,
    )