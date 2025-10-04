# rewards/control_views.py
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, F, Q
from django.contrib import messages
from django.urls import reverse
from .forms import RewardItemForm, GiftAdHocForm
from tickets.models import TicketType
from .models import RewardsAccount, PointsLedger, PurchaseRecord, RewardItem, Redemption
from shop.models import Product
from django.db import transaction
from .services import _fulfill_product_without_variant, create_pending_gift_redemption
from django.contrib.contenttypes.models import ContentType

is_super = user_passes_test(lambda u: u.is_superuser)

@is_super
def overview(request):
    accounts = RewardsAccount.objects.count()
    total_points = RewardsAccount.objects.aggregate(s=Sum("points_balance"))["s"] or 0
    pending_redemptions = Redemption.objects.filter(fulfilled=False).count()
    purchases = PurchaseRecord.objects.count()
    top_accounts = (RewardsAccount.objects
                    .select_related("user")
                    .order_by("-points_balance")[:10])
    recent_ledger = PointsLedger.objects.select_related("account","account__user").order_by("-created_at")[:20]
    return render(request, "rewards/control/overview.html", {
        "metrics": {
            "accounts": accounts,
            "total_points": total_points,
            "pending_redemptions": pending_redemptions,
            "purchases": purchases,
        },
        "top_accounts": top_accounts,
        "recent_ledger": recent_ledger,
    })

@is_super
def accounts(request):
    q = (request.GET.get("q") or "").strip()
    qs = RewardsAccount.objects.select_related("user").order_by("-points_balance")
    if q:
        qs = qs.filter(Q(user__email__icontains=q)|Q(user__username__icontains=q))
    return render(request, "rewards/control/accounts.html", {"accounts": qs[:500], "q": q})

@is_super
def account_detail(request, user_id):
    acc = get_object_or_404(RewardsAccount.objects.select_related("user"), user_id=user_id)
    ledger = PointsLedger.objects.filter(account=acc).order_by("-created_at")[:500]
    purchases = PurchaseRecord.objects.filter(Q(account=acc)|Q(email__iexact=acc.user.email)).order_by("-created_at")[:200]
    redemptions = Redemption.objects.filter(account=acc).order_by("-created_at")
    return render(request, "rewards/control/account_detail.html", {
        "acc": acc, "ledger": ledger, "purchases": purchases, "redemptions": redemptions
    })

@is_super
def purchases(request):
    kind = request.GET.get("kind") or ""
    q = (request.GET.get("q") or "").strip()
    qs = PurchaseRecord.objects.select_related("account","account__user","guest").order_by("-created_at")
    if kind in ("ORDER","TICKET"):
        qs = qs.filter(kind=kind)
    if q:
        qs = qs.filter(Q(external_id__icontains=q)|Q(email__icontains=q)|Q(account__user__email__icontains=q))
    return render(request, "rewards/control/purchases.html", {"rows": qs[:1000], "kind": kind, "q": q})

@is_super
def redemptions(request):
    qs = Redemption.objects.select_related("account","account__user","item").order_by("-created_at")
    if request.method == "POST":
        ids = request.POST.getlist("rid")
        if ids:
            Redemption.objects.filter(id__in=ids).update(fulfilled=True)
            messages.success(request, f"Marked {len(ids)} redemptions fulfilled.")
        return redirect(reverse("rewards_control:redemptions"))
    return render(request, "rewards/control/redemptions.html", {"rows": qs})

@is_super
def reward_items_list(request):
    qs = RewardItem.objects.all().order_by("-is_active","points_cost","name")
    return render(request, "rewards/control/reward_items.html", {"items": qs})

@is_super
def reward_item_new(request):
    form = RewardItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(request, f"Added reward: {item.name}")
        return redirect("control:rewards_control:items")
    return render(request, "rewards/control/reward_item_form.html", {"form": form, "mode": "new"})

@is_super
def reward_item_edit(request, pk):
    item = get_object_or_404(RewardItem, pk=pk)
    form = RewardItemForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Updated reward: {item.name}")
        return redirect("control:rewards_control:items")
    return render(request, "rewards/control/reward_item_form.html", {"form": form, "mode": "edit", "item": item})

@is_super
def reward_item_delete(request, pk):
    item = get_object_or_404(RewardItem, pk=pk)
    if request.method == "POST":
        name = item.name
        item.delete()
        messages.success(request, f"Deleted reward: {name}")
        return redirect("control:rewards_control:items")
    # simple safety: redirect back if GET
    return redirect("control:rewards_control:items")

@is_super
def gift_reward(request):
    """
    Ad-hoc gifts:
      - TICKET: issue N comp tickets for chosen TicketType to user.email
      - PRODUCT: create $0 comp order with N of the chosen Product for the user
    Everything is private to the recipient; no RewardItem is created.
    """
    form = GiftAdHocForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.cleaned_data["user"]
        rt = form.cleaned_data["reward_type"]
        qty = form.cleaned_data["quantity"]
        note = form.cleaned_data.get("note") or ""
        email_user = form.cleaned_data.get("email_recipient", True)

        # ensure they have a rewards account (for PurchaseRecord linkage)
        acc, _ = RewardsAccount.objects.get_or_create(user=user)

        # try:
        with transaction.atomic():
            if rt == "TICKET":
                tt: TicketType = form.cleaned_data["ticket_type"]
                ri, _ = RewardItem.objects.get_or_create(
                    sku=f"_GIFT_TT_{tt.pk}",
                    defaults={
                        "name": f"Gift: {tt.event.name} — {tt.name}",
                        "description": "Private gift ticket",
                        "points_cost": 0,
                        "inventory": 10**9,
                        "is_active": False,
                        "fulfill_type": "TICKET",
                        "quantity_per_redeem": 1,
                    }
                )
                ri.target_ct = ContentType.objects.get_for_model(TicketType)
                ri.target_id = tt.pk
                ri.save(update_fields=["target_ct","target_id"])

                # ⬇️ Create a pending redemption (no issuance yet)
                create_pending_gift_redemption(
                    account=acc, item=ri, quantity=qty, note=note
                )
                messages.success(request, f"Created a gift: {qty} ticket(s) for {tt.event.name} — {tt.name}. The user can redeem from their Passport.")

            elif rt == "PRODUCT":
                product: Product = form.cleaned_data["product"]
                # Build a transient RewardItem-like wrapper, or create a private/system reward item:
                # Easiest: make (or get) a dedicated internal RewardItem per product for fulfillment.
                ri, _ = RewardItem.objects.get_or_create(
                    sku=f"_GIFT_PROD_{product.pk}",
                    defaults={
                        "name": f"Gift: {product.title}",
                        "description": "Private gift item",
                        "points_cost": 0,
                        "inventory": 10**9,   # logical cap; not used for gifts
                        "is_active": False,
                        "fulfill_type": "PRODUCT",
                        "quantity_per_redeem": 1,
                        # target set below
                    }
                )
                # map target
                ri.target_ct = ContentType.objects.get_for_model(Product)
                ri.target_id = product.pk
                ri.save(update_fields=["target_ct","target_id"])

                # Products with variants -> pending; without variants -> auto-fulfill now
                if getattr(product, "has_variants", False):
                    create_pending_gift_redemption(
                        account=acc, item=ri, quantity=qty, note=note
                    )
                    messages.success(request, f"Gifted {product.title}. Recipient will choose a variant when redeeming.")
                else:
                    # Create pending, then fulfill immediately
                    red = create_pending_gift_redemption(
                        account=acc, item=ri, quantity=qty, note=note
                    )
                    _fulfill_product_without_variant(account=acc, product=product, qty=qty, redemption=red)
                    if hasattr(red, "mark_fulfilled"):
                        red.mark_fulfilled()
                    else:
                        red.status = "FULFILLED"; red.fulfilled = True; red.save(update_fields=["status","fulfilled"])
                    messages.success(request, f"Gifted {qty} × {product.title} to {user.email} (auto-fulfilled).")
            else:
                messages.error(request, "Unsupported reward type.")
                return redirect("control:rewards_control:gift")
        # except Exception as e:
        #     messages.error(request, f"Could not gift reward: {e}")
        #     return redirect("control:rewards_control:gift")
        return redirect("control:rewards_control:items")
    return render(request, "rewards/control/gift_reward.html", {"form": form})