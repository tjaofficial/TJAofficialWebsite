# rewards/services.py
from __future__ import annotations
from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from typing import Optional
from .models import RewardsAccount, Redemption, PurchaseRecord, RewardItem
from django.db.models import F
from shop.models import Product, Order, OrderItem
from tickets.models import TicketType, Ticket
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
# External models we might fulfill against:
from shop.models import Product
from tickets.models import TicketType, Ticket
from coreutils.mailer import send_tickets_email  # you already use this

User = get_user_model()

class RedemptionError(Exception): ...

@transaction.atomic
def redeem_item(*, account, item, use_points=None, via_code=None):
    """
    Auto-fulfills tickets. For products:
      - If product.has_variants: create PENDING redemption and return (user must select variant)
      - Else: fulfill immediately (create $0 order if needed) and decrement inventory.
    """
    qty = max(1, int(getattr(item, "quantity_per_redeem", 1)))
    cost = 0 if use_points in (None, 0) else int(item.points_cost)

    # charge points (unless use_points=0 forced for gifts)
    if cost and account.points_balance < cost:
        raise RedemptionError("Not enough points.")
    if cost:
        account.apply_ledger(delta=-cost, kind="REDEEM", source="MANUAL", ref=f"item:{item.id}")

    red = Redemption.objects.create(
        account=account,
        item=item,
        points_spent=cost,
        quantity=qty,
        status="FULFILLED",  # may switch to PENDING
        fulfilled=False,     # set true only after finalize
    )

    if item.fulfill_type == "TICKET":
        # existing ticket auto-fulfillment (as you had)
        # issue N tickets for item.target_id (TicketType)
        # ... (unchanged) ...
        _fulfill_tickets(account, item, qty, redemption=red)  # your existing helper
        red.mark_fulfilled()
        return red

    if item.fulfill_type == "PRODUCT":
        product = Product.objects.filter(pk=item.target_id).first()
        if not product:
            raise RedemptionError("Product not found.")

        if product.has_variants:
            # Defer fulfillment until the user selects a variant
            red.status = "PENDING"
            red.save(update_fields=["status"])
            # (Optionally email user: “choose your size” with link)
            return red

        # No variants? fulfill now
        _fulfill_product_without_variant(account, product, qty, redemption=red)
        red.mark_fulfilled()
        return red

    # fallback/custom
    red.mark_fulfilled()
    return red

def _fulfill_redemption(red: Redemption):
    item = red.item
    qty = max(1, item.quantity_per_redeem)

    if item.fulfill_type == "PRODUCT":
        # Create a free order (or an internal fulfillment note).
        # Simplest: decrement product inventory and mark redemption fulfilled.
        if item.target and isinstance(item.target, Product):
            Product.objects.filter(pk=item.target.pk).update(inventory=F("inventory") - qty)
        red.fulfilled = True
        red.save(update_fields=["fulfilled"])

    elif item.fulfill_type == "TICKET":
        if not item.target or not isinstance(item.target, TicketType):
            return
        tickets = []
        for _ in range(qty):
            t = Ticket.objects.create(
                ticket_type=item.target,
                purchaser_email=red.account.user.email,
                purchaser_name=red.account.user.get_full_name() or red.account.user.username,
                payment_method="comp",
            )
            tickets.append(t)
        # email QR
        if tickets and red.account.user.email:
            send_tickets_email(red.account.user.email, tickets)
        red.fulfilled = True
        red.save(update_fields=["fulfilled"])

    elif item.fulfill_type == "COUPON":
        # Optionally create a one-off 100% off coupon for this user
        from shop.models import Coupon
        code = f"RWD-{red.id}"
        Coupon.objects.create(
            code=code,
            percent_off=100,
            single_use=True,
            note=f"Reward for {red.account.user.email}",
        )
        red.notes = (red.notes or "") + f"\nCoupon: {code}"
        red.fulfilled = True
        red.save(update_fields=["notes","fulfilled"])

    else:
        # CUSTOM: manual fulfillment by ops
        pass

def _fulfill_product_without_variant(*, account: RewardsAccount, product: Product, qty: int, redemption: Redemption | None = None,) -> Order:
    """
    Create a $0 comp Order for a product with NO variants and decrement inventory.
    Records a PurchaseRecord so it appears in the user's Passport history.
    """
    user = account.user
    now = timezone.now()

    # Comp order shell
    order = Order.objects.create(
        user=user,
        email=user.email or "",
        status="paid",
        number=f"REDEEM-{now.strftime('%Y%m%d%H%M%S')}-{(redemption.pk if redemption else 'P')}",
        subtotal_cents=0,
        shipping_cents=0,
        tax_cents=0,
        total_cents=0,
        payment_provider="comp",
        provider_session_id="",
        provider_payment_intent="",
        paid_at=now,
        ship_to_name=(user.get_full_name() or user.username or user.email or "Member"),
    )

    # Line item (no variant)
    OrderItem.objects.create(
        order=order,
        product=product,
        variant=None,
        title_snapshot=product.title,
        size="",
        qty=qty,
        price_cents_snapshot=0,  # free
    )

    # Decrement product inventory (if you don't want to count gifts against stock, comment this out)
    Product.objects.filter(pk=product.pk).update(inventory=F("inventory") - qty)

    # Normalized purchase record
    PurchaseRecord.objects.create(
        kind="ORDER",
        external_id=order.number or str(order.pk),
        account=account,
        subtotal_cents=0,
        currency="USD",
        email=user.email or "",
        meta={
            "redeem": True,
            "gift": (redemption.points_spent == 0 if redemption else False),
            "product": product.title,
            "qty": qty,
            "redemption_id": redemption.pk if redemption else None,
        },
    )

    return order

@transaction.atomic
def _fulfill_tickets(*, account, ticket_type: TicketType, qty: int, redemption=None):
    """
    Issue `qty` comp tickets for `ticket_type` to account.user.email.
    Returns list[Ticket]. Safe to call from redeem flow.
    """
    user: AbstractUser = account.user
    created = []
    name = (user.get_full_name() or user.username or user.email or "").strip()

    for _ in range(int(max(1, qty))):
        t = Ticket.objects.create(
            ticket_type=ticket_type,
            purchaser_email=user.email,
            purchaser_name=name,
            payment_method="comp",
            # sold_by_user could be set to the admin gifting user if you’re passing it in
        )
        created.append(t)

    # Email the tickets (don’t fail redemption if email breaks)
    try:
        if created:
            send_tickets_email(user.email, created)
    except Exception:
        pass

    return created

@transaction.atomic
def create_pending_gift_redemption(*, account: RewardsAccount, item: RewardItem, quantity: int = 1, note: str = "") -> Redemption:
    """
    Create a 0-point, PENDING redemption. Nothing is fulfilled yet.
    Recipient will click 'Redeem' later (which triggers fulfillment).
    """
    red = Redemption.objects.create(
        account=account,
        item=item,
        points_spent=0,
        quantity=max(1, int(quantity)),
        status="PENDING",
        fulfilled=False,
        notes=note or "Gift",
    )
    return red