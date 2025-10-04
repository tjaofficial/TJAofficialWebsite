# rewards/integrations.py
from __future__ import annotations
from typing import TYPE_CHECKING
from django.apps import apps
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone

from .utils import record_store_order, record_ticket_checkin
from .models import PurchaseRecord, RewardsAccount, GuestCustomer

# --- ORDER: award when status flips to "paid" ---
Order = apps.get_model("shop", "Order")  # adjust app label if different
Ticket = apps.get_model("tickets", "Ticket")  # adjust app label if different

if TYPE_CHECKING:
    from shop.models import Order as ShopOrder
    from tickets.models import Ticket as TicketsTicket

@receiver(pre_save, sender=Order)
def rewards_on_order_paid(sender, instance: "ShopOrder", **kwargs):
    if not instance.pk:
        return
    try:
        prev = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if prev.status != "paid" and instance.status == "paid":
        # de-dupe: only create once per order.number or pk
        ref = instance.number or str(instance.pk)
        if PurchaseRecord.objects.filter(kind="ORDER", external_id=ref).exists():
            return  # already recorded (safety)

        # prefer subtotal for points (pre tax/shipping)
        subtotal_cents = int(getattr(instance, "subtotal_cents", 0)) or 0

        # user (logged in) or guest via email
        user = instance.user if getattr(instance, "user_id", None) else None
        email = instance.email if not user else None

        meta = {
            "number": instance.number,
            "shipping_cents": instance.shipping_cents,
            "tax_cents": instance.tax_cents,
            "total_cents": instance.total_cents,
            "ship": {
                "name": instance.ship_to_name,
                "addr1": instance.ship_to_addr1,
                "city": instance.ship_to_city,
                "state": instance.ship_to_state,
                "postal": instance.ship_to_postal,
                "method": instance.shipping_method,
            },
            "payment": {
                "provider": instance.payment_provider,
                "session_id": instance.provider_session_id,
                "payment_intent": instance.provider_payment_intent,
            },
        }

        # Award & persist PurchaseRecord (USD by default)
        record_store_order(
            order_id=ref,
            subtotal_cents=subtotal_cents,
            currency="USD",
            user=user,
            email=email,
            phone=None,  # add if you capture phone on orders
            meta=meta,
        )



@receiver(post_save, sender=Ticket)
def rewards_on_ticket_checkin(sender, instance: "TicketsTicket", created: bool, **kwargs):
    # Only act if this save created or toggled the check-in timestamp from None -> value
    if not instance.checked_in_at:
        return

    ref = str(instance.pk)  # or use str(instance.qr_token)
    if PurchaseRecord.objects.filter(kind="TICKET", external_id=ref).exists():
        return  # already awarded (safety)

    # This model doesn't have a purchaser user; we use purchaser_email as a guest (or to merge later)
    record_ticket_checkin(
        ticket_id=ref,
        user=None,
        email=(instance.purchaser_email or None),
        phone=None,
        meta={
            "ticket_type": getattr(instance.ticket_type, "name", ""),
            "payment_method": instance.payment_method,
            "sold_by_artist_id": getattr(instance.sold_by_artist, "id", None),
            "sold_by_user_id": getattr(instance.sold_by_user, "id", None),
            "checked_in_at": instance.checked_in_at.isoformat() if instance.checked_in_at else None,
        },
    )
