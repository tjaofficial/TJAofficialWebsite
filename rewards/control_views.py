# rewards/control_views.py
from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Count, Q
from django.contrib import messages
from django.urls import reverse

from .models import RewardsAccount, PointsLedger, PurchaseRecord, RewardItem, Redemption, GuestCustomer
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
