from django.db.models.signals import post_save
from django.dispatch import receiver

from tickets.models import Ticket
from .views import split_name_parts, upsert_subscriber_from_email


@receiver(post_save, sender=Ticket)
def create_or_update_subscriber_from_ticket(sender, instance, created, **kwargs):
    email = (instance.purchaser_email or "").strip().lower()
    if not email:
        return

    first_name, last_name = split_name_parts(instance.purchaser_name)
    upsert_subscriber_from_email(
        email=email,
        first_name=first_name,
        last_name=last_name,
        source="ticket_purchase",
    )