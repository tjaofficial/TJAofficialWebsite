from __future__ import annotations
from decimal import Decimal
from django.db import transaction
from django.contrib.auth import get_user_model
from .models import RewardsAccount, GuestCustomer, PurchaseRecord, PointsLedger, EarningRule
from django.contrib.auth.models import AbstractUser

User = get_user_model()

def _user_phone(user):
    phone = None
    prof = getattr(user, "profile", None) or getattr(user, "rewards_profile", None)
    if prof and getattr(prof, "phone", None):
        phone = prof.phone
    return phone

@transaction.atomic
def record_store_order(*, order_id:str, subtotal_cents:int, currency:str="USD", user:AbstractUser|None=None,
    email:str|None=None, phone:str|None=None, meta:dict|None=None):
    """
    Call this once when an order is paid/captured. If user is None, we’ll file it under a GuestCustomer.
    Awards points using active PER_DOLLAR rule (default 2 pts/$) and writes a PurchaseRecord.
    """
    acc = None
    guest = None
    if user:
        acc, _ = RewardsAccount.objects.get_or_create(user=user)
    else:
        if not email and not phone:
            raise ValueError("Guest purchase requires email or phone")
        guest, _ = GuestCustomer.objects.get_or_create(email=email or "guest@example.com", defaults={"phone": phone or ""})
        if phone and not guest.phone:
            guest.phone = phone
            guest.save(update_fields=["phone"])


    pr = PurchaseRecord.objects.create(
        kind="ORDER",
        external_id=str(order_id),
        subtotal_cents=subtotal_cents,
        currency=currency,
        account=acc,
        guest=guest,
        email=(user.email if user else (email or "")),
        phone=(_user_phone(user) if (user and hasattr(user, "profile")) else (phone or "")),
        meta=meta or {},
    )


    # Points: PER_DOLLAR
    rule = EarningRule.objects.filter(rule_type="PER_DOLLAR", active=True).order_by("-id").first()
    multiplier = Decimal(rule.multiplier) if rule else Decimal("2.0") # default 2 pts/$
    dollars = Decimal(subtotal_cents) / Decimal(100)
    points = int(dollars * multiplier)


    if acc and points:
        acc.apply_ledger(delta=points, kind="EARN", source="ORDER", ref=str(order_id), meta={"currency": currency, "subtotal_cents": subtotal_cents})


    return pr, points

@transaction.atomic
def record_ticket_checkin(*, ticket_id:str, user:AbstractUser|None=None, email:str|None=None, phone:str|None=None, meta:dict|None=None):
    """
    Call this when a ticket is successfully checked in at the door.
    If user is None but email belongs to an existing account, we attach to that account and award points.
    Otherwise, we log it as a guest purchase; points can be retro-awarded via merge.
    """
    acc = None
    guest = None

    if user is None and email:
        matched_user = User.objects.filter(email__iexact=email).first()
        if matched_user:
            user = matched_user  # treat as an account check-in

    if user:
        acc, _ = RewardsAccount.objects.get_or_create(user=user)
    else:
        if not email and not phone:
            raise ValueError("Guest check‑in requires email or phone")
        guest, _ = GuestCustomer.objects.get_or_create(email=email or "guest@example.com", defaults={"phone": phone or ""})
        if phone and not guest.phone:
            guest.phone = phone
            guest.save(update_fields=["phone"])

    pr = PurchaseRecord.objects.create(
        kind="TICKET",
        external_id=str(ticket_id),
        account=acc,
        guest=guest,
        email=(user.email if user else (email or "")),
        phone=(_user_phone(user) if (user and hasattr(user, "profile")) else (phone or "")),
        meta=meta or {},
    )

    # Points: PER_TICKET (default 5)
    rule = EarningRule.objects.filter(rule_type="PER_TICKET", active=True).order_by("-id").first()
    points = int(rule.multiplier) if rule else 5

    if acc and points:
        acc.apply_ledger(delta=points, kind="EARN", source="TICKET", ref=str(ticket_id), meta=meta or {})

    return pr, points

@transaction.atomic
def merge_guest_into_user(*, user:AbstractUser, email:str):
    """On signup or later: attach historical guest purchases to the user’s RewardsAccount and retro‑award points."""
    acc, _ = RewardsAccount.objects.get_or_create(user=user)
    try:
        guest = GuestCustomer.objects.get(email=email)
    except GuestCustomer.DoesNotExist:
        return 0

    moved = 0
    for pr in guest.purchases.select_related("guest").all():
        pr.account = acc
        pr.guest = None
        pr.save(update_fields=["account", "guest"])
        # Retro points: only if not already awarded (we only award when account exists). Award both ORDER and TICKET.
        if pr.kind == "ORDER":
            from decimal import Decimal
            rule = EarningRule.objects.filter(rule_type="PER_DOLLAR", active=True).order_by("-id").first()
            multiplier = Decimal(rule.multiplier) if rule else Decimal("2.0")
            dollars = Decimal(pr.subtotal_cents) / Decimal(100)
            pts = int(dollars * multiplier)
            if pts:
                acc.apply_ledger(delta=pts, kind="EARN", source="ORDER", ref=f"retro:{pr.external_id}")
                moved += pts
        elif pr.kind == "TICKET":
            rule = EarningRule.objects.filter(rule_type="PER_TICKET", active=True).order_by("-id").first()
            pts = int(rule.multiplier) if rule else 5
            if pts:
                acc.apply_ledger(delta=pts, kind="EARN", source="TICKET", ref=f"retro:{pr.external_id}")
                moved += pts
    return moved

