# rewards/services.py
from __future__ import annotations
from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from typing import Optional
from .models import RewardsAccount, RewardItem, Redemption, GiftCode
from .models import PointsLedger, EarningRule  # optional for audit
from django.db.models import F

# External models we might fulfill against:
from shop.models import Product
from tickets.models import TicketType, Ticket
from coreutils.mailer import send_tickets_email  # you already use this

class RedemptionError(Exception): ...

@transaction.atomic
def redeem_item(*, account: RewardsAccount, item: RewardItem, use_points: Optional[int]=None, via_code: GiftCode|None=None) -> Redemption:
    if not item.is_active:
        raise RedemptionError("This item is not active.")
    if item.inventory <= 0:
        raise RedemptionError("Sorry, this reward is out of stock.")

    cost = item.points_cost if use_points is None else int(use_points)
    if via_code and via_code.points_cost_override is not None:
        cost = int(via_code.points_cost_override)

    # check balance (unless cost is 0)
    if cost > 0 and account.points_balance < cost:
        raise RedemptionError("Not enough points.")

    # deduct points
    if cost > 0:
        account.apply_ledger(delta=-cost, kind="REDEEM", source="MANUAL", ref=f"REWARD:{item.sku}", meta={"item": item.name})

    # reserve inventory
    item.inventory = item.inventory - 1
    item.save(update_fields=["inventory"])

    red = Redemption.objects.create(
        account=account,
        item=item,
        points_spent=cost,
        fulfilled=False,
        notes=("Gift code: " + via_code.code) if via_code else "",
    )

    # mark gift code used
    if via_code:
        via_code.redeemed_at = timezone.now()
        via_code.redeemed_by = account
        via_code.save(update_fields=["redeemed_at","redeemed_by"])

    # fulfill immediately (or you can leave to ops)
    _fulfill_redemption(red)
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
