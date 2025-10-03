from __future__ import annotations
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
from .models import RewardsAccount, RewardItem, Redemption, CustomerProfile, PurchaseRecord
from .utils import merge_guest_into_user
from django.contrib.auth import login
from .forms import SignupForm
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.apps import apps

User = get_user_model()

@login_required
def dashboard(request):
    acc, _ = RewardsAccount.objects.get_or_create(user=request.user)

    # Ledger & redemptions for the existing sections
    ledger = acc.ledger.select_related().all()[:100]
    redemptions = acc.redemptions.select_related("item").order_by("-created_at")
    reward_items = RewardItem.objects.filter(is_active=True, inventory__gt=0).order_by("points_cost")

    # --- Purchase history (normalized from PurchaseRecord) ---
    # Show most recent 50 across orders+tickets; you can paginate later.
    purchases = PurchaseRecord.objects.filter(
        Q(account=acc) | Q(email__iexact=request.user.email)
    ).order_by("-created_at", "-id")[:50]

    # --- Active tickets (unchecked-in) ---
    Ticket = None
    active_tickets = []
    try:
        Ticket = apps.get_model("tickets", "Ticket")  # adjust app label if yours differs
    except Exception:
        Ticket = None

    if Ticket:
        # Tickets known via PurchaseRecord (linked to this account)
        ticket_ids = list(
            PurchaseRecord.objects.filter(
                Q(account=acc) | Q(email__iexact=request.user.email),
                kind="TICKET"
            ).values_list("external_id", flat=True)
        )

        # Build a query that captures:
        #  - Tickets referenced in PurchaseRecord
        #  - PLUS any tickets purchased with user's email (fallback)
        q = Q(checked_in_at__isnull=True)
        if ticket_ids:
            q &= (Q(pk__in=ticket_ids) | Q(purchaser_email__iexact=request.user.email))
        else:
            q &= Q(purchaser_email__iexact=request.user.email)

        active_tickets = list(
            Ticket.objects.filter(q).select_related("ticket_type").order_by("-issued_at")[:50]
        )

    return render(
        request,
        "rewards/dashboard.html",
        {
            "account": acc,
            "ledger": ledger,
            "redemptions": redemptions,
            "items": reward_items,
            "purchases": purchases,
            "active_tickets": active_tickets,
        },
    )

@login_required
@require_POST
def redeem(request, item_id):
    acc, _ = RewardsAccount.objects.get_or_create(user=request.user)
    item = get_object_or_404(RewardItem, pk=item_id, is_active=True)
    if acc.points_balance < item.points_cost:
        messages.error(request, "Not enough points.")
        return redirect("rewards:dashboard")
    # reserve inventory
    if item.inventory <= 0:
        messages.error(request, "Item out of stock.")
        return redirect("rewards:dashboard")
    item.inventory -= 1
    item.save(update_fields=["inventory"])
    acc.apply_ledger(delta=-item.points_cost, kind="REDEEM", source="MANUAL", ref=f"reward:{item.id}")
    Redemption.objects.create(account=acc, item=item, points_spent=item.points_cost)
    messages.success(request, f"Redeemed {item.name}")
    
    return redirect("rewards:dashboard")

@login_required
@require_POST
def merge_history(request):
    email = request.POST.get("email")
    moved = merge_guest_into_user(user=request.user, email=email)
    if moved:
        messages.success(request, f"Merged history and added {moved} points from guest purchases.")
    else:
        messages.info(request, "No guest history found for that email.")
    return redirect("rewards:dashboard")

# (Optional) simple staff view wrapper – use Django admin for most staff tasks
@user_passes_test(lambda u: u.is_staff)
def staff_snapshot(request):
    return render(request, "rewards/staff_snapshot.html")

@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        messages.info(request, "You're already signed in.")
        return redirect("rewards:dashboard")

    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        password = form.cleaned_data["password"]

        # Create user
        username = form.cleaned_data["username"].strip()
        last_name = form.cleaned_data.get("last_name").strip()
        first_name = form.cleaned_data.get("first_name").strip()
        user = User.objects.create_user(username=username, email=email, password=password, first_name=first_name, last_name=last_name)

        # Ensure rewards/profile exist (signals will create, but we want to persist fields now)
        profile, _ = CustomerProfile.objects.get_or_create(user=user)
        profile.phone = form.cleaned_data.get("phone") or ""
        profile.birthday = form.cleaned_data.get("birthday")
        profile.sex = form.cleaned_data.get("sex") or ""
        profile.ship_name = form.cleaned_data.get("ship_name") or ""
        profile.ship_line1 = form.cleaned_data.get("ship_line1") or ""
        profile.ship_line2 = form.cleaned_data.get("ship_line2") or ""
        profile.ship_city = form.cleaned_data.get("ship_city") or ""
        profile.ship_state = form.cleaned_data.get("ship_state") or ""
        profile.ship_postal = form.cleaned_data.get("ship_postal") or ""
        profile.ship_country = (form.cleaned_data.get("ship_country") or "US").upper()
        profile.marketing_opt_in = bool(form.cleaned_data.get("marketing_opt_in"))
        profile.save()

        # Rewards account (created by signal; also safe to get/create)
        RewardsAccount.objects.get_or_create(user=user)

        # Log them in
        login(request, user)

        messages.success(request, "Welcome! Your account is ready. +10 points added for signing up 🎉")
        return redirect("rewards:dashboard")

    return render(request, "rewards/signup.html", {"form": form})