from __future__ import annotations
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
from .models import RewardsAccount, RewardItem, Redemption, CustomerProfile, PurchaseRecord, GiftCode
from .utils import merge_guest_into_user
from django.contrib.auth import login
from .forms import SignupForm
from django.contrib.auth import get_user_model
from django.db.models import Q, F
from django.apps import apps
from .services import redeem_item, RedemptionError
from django.db import transaction
from shop.models import Product, ProductVariant, Order, OrderItem
from django.utils import timezone
from .services import _fulfill_product_without_variant, _fulfill_tickets
from coreutils.mailer import send_notification_update
from coreutils.mailer_activation import send_activation_email
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django import forms
from django.conf import settings

User = get_user_model()
SIGNUP_BONUS_POINTS = 10

@login_required
def dashboard(request):
    acc, _ = RewardsAccount.objects.get_or_create(user=request.user)

    balance = acc.points_balance
    # What you can afford right now (and in stock)
    affordable = (RewardItem.objects
                  .filter(is_active=True, inventory__gt=0, points_cost__lte=balance)
                  .order_by("points_cost", "name")[:24])
    # Ledger & redemptions for the existing sections
    ledger = acc.ledger.select_related().all()[:100]
    redemptions = acc.redemptions.select_related("item").order_by("-created_at")
    reward_items = RewardItem.objects.filter(is_active=True, inventory__gt=0).order_by("points_cost")

    # --- Purchase history (normalized from PurchaseRecord) ---
    # Show most recent 50 across orders+tickets; you can paginate later.
    purchases = (PurchaseRecord.objects
        .filter(Q(account=acc) | Q(email__iexact=request.user.email))
        .exclude(meta__gift=True) 
        .order_by("-created_at", "-id")[:50]
    )

    pending_gifts = acc.redemptions.select_related("item").filter(
        points_spent=0, fulfilled=False
    ).order_by("-created_at")

    # ✅ Find the FIRST pending redemption that needs a product variant
    pending_variant = next(
        (r for r in redemptions
         if r.status == "PENDING" and getattr(r.item, "fulfill_type", "") == "PRODUCT"),
        None
    )

    Ticket = None
    active_tickets = []
    try:
        Ticket = apps.get_model("tickets", "Ticket")
    except Exception:
        Ticket = None

    if Ticket:
        active_tickets = list(
            Ticket.objects
                .select_related("ticket_type", "ticket_type__event")
                .filter(
                    Q(purchaser_email__iexact=request.user.email),
                    Q(checked_in_at__isnull=True),
                )
                .order_by("-issued_at")[:50]
        )

    return render(request, "rewards/dashboard.html",{
        "account": acc,
        "balance": balance,
        "affordable": affordable,
        "ledger": ledger,
        "redemptions": redemptions,
        "items": reward_items,
        "purchases": purchases,
        "pending_variant": pending_variant,
        "pending_gifts": pending_gifts,
        'active_tickets': active_tickets,
    })

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

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            # make user inactive until email verified
            user.is_active = False
            user.save(update_fields=["is_active"])

            # profile fields
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

            newAccount, created = RewardsAccount.objects.get_or_create(user=user)

        # send activation
        send_activation_email(user, request=request)
        send_notification_update('rewards', newAccount, request=request)
        messages.success(request, "Check your email to activate your account.")
        return redirect("control:accounts:login")  # or a “check your email” page

    return render(request, "rewards/signup.html", {"form": form})

@login_required
def catalog(request):
    acc = request.user.rewards  # RewardsAccount (created on signup)
    items = RewardItem.objects.filter(is_active=True).order_by("points_cost","name")
    return render(request, "rewards/catalog.html", {"items": items, "balance": acc.points_balance})

@login_required
def redeem(request, item_id):
    if request.method != "POST":
        return redirect("rewards:dashboard")
    acc = request.user.rewards
    item = get_object_or_404(RewardItem, pk=item_id, is_active=True, inventory__gt=0)
    try:
        redeem_item(account=acc, item=item)  # auto-fulfills (tickets are specific shows)
        messages.success(request, f"Redeemed {item.name}!")
    except RedemptionError as e:
        messages.error(request, str(e))
    return redirect("rewards:dashboard")

@login_required
def claim_code(request):
    if request.method != "POST":
        return redirect("rewards:dashboard")
    code = (request.POST.get("code") or "").strip().upper()
    gc = GiftCode.objects.filter(code=code).first()
    if not gc:
        messages.error(request, "Invalid code.")
        return redirect("rewards:dashboard")
    if gc.is_expired():
        messages.error(request, "This code is expired.")
        return redirect("rewards:dashboard")
    if gc.is_redeemed():
        messages.error(request, "This code was already redeemed.")
        return redirect("rewards:dashboard")
    if gc.email_restricted and gc.email_restricted.lower() != request.user.email.lower():
        messages.error(request, "This code is restricted to a different email.")
        return redirect("rewards:dashboard")

    acc = request.user.rewards
    try:
        redeem_item(account=acc, item=gc.item, via_code=gc)  # auto-fulfills
        messages.success(request, f"{gc.item.name} claimed!")
    except RedemptionError as e:
        messages.error(request, str(e))
    return redirect("rewards:dashboard")

@login_required
def choose_variant(request, redemption_id):
    red = get_object_or_404(Redemption.objects.select_related("item","account__user"), pk=redemption_id)
    if red.account.user_id != request.user.id:
        messages.error(request, "Not authorized.")
        return redirect("rewards:dashboard")

    if red.status != "PENDING" or red.item.fulfill_type != "PRODUCT":
        messages.info(request, "Nothing to do for this redemption.")
        return redirect("rewards:dashboard")

    product = Product.objects.filter(pk=red.item.target_id).first()
    if not product or not product.has_variants:
        messages.error(request, "This item no longer requires variant selection.")
        return redirect("rewards:dashboard")

    variants = product.variants.filter(is_active=True, inventory__gt=0).order_by("size")
    if request.method == "POST":
        try:
            variant_id = int(request.POST.get("variant_id") or 0)
        except ValueError:
            variant_id = 0
        variant = variants.filter(pk=variant_id).first()
        if not variant:
            messages.error(request, "Please choose an in-stock variant.")
            return redirect("rewards:choose_variant", redemption_id=red.pk)

        # Fulfill with this variant
        with transaction.atomic():
            # Create $0 order (comp) for traceability
            order = Order.objects.create(
                user=request.user,
                email=request.user.email,
                status="paid",
                number=f"REDEEM-{timezone.now().strftime('%Y%m%d%H%M%S')}-{red.pk}",
                subtotal_cents=0, shipping_cents=0, tax_cents=0, total_cents=0,
                payment_provider="comp",
                paid_at=timezone.now(),
                ship_to_name=request.user.get_full_name() or request.user.username,
            )
            OrderItem.objects.create(
                order=order,
                product=product,
                variant=variant,
                title_snapshot=product.title,
                size=getattr(variant, "size", ""),
                qty=red.quantity,
                price_cents_snapshot=0,
            )
            # decrement the chosen variant inventory
            ProductVariant.objects.filter(pk=variant.pk).update(inventory=F("inventory") - red.quantity)

            # link & mark redemption
            red.selected_variant = variant
            red.mark_fulfilled()

            # record purchase for dashboard
            PurchaseRecord.objects.create(
                kind="ORDER",
                external_id=order.number or str(order.pk),
                account=red.account,
                subtotal_cents=0,
                currency="USD",
                email=request.user.email,
                meta={"redeem": True, "product": product.title, "variant": getattr(variant, "size", ""), "qty": red.quantity},
            )

        messages.success(request, f"Fulfilled {product.title} — {getattr(variant, 'size', '')}.")
        return redirect("rewards:dashboard")

    return render(request, "rewards/choose_variant.html", {
        "redemption": red,
        "product": product,
        "variants": variants,
    })

@login_required
@require_POST
def redeem_redemption(request, pk):
    red = get_object_or_404(Redemption.objects.select_related("item", "account", "account__user"), pk=pk)

    # Security: ensure this redemption belongs to the current user
    if red.account.user_id != request.user.id:
        messages.error(request, "This gift does not belong to your account.")
        return redirect("rewards:dashboard")

    if red.fulfilled or red.status == "FULFILLED":
        messages.info(request, "Already redeemed.")
        return redirect("rewards:dashboard")

    item = red.item
    try:
        if item.fulfill_type == "TICKET":
            # issue comp tickets now
            from tickets.models import TicketType
            tt = None
            if item.target_ct and item.target_ct.model == "tickettype":
                from django.contrib.contenttypes.models import ContentType
                tt = TicketType.objects.filter(pk=item.target_id).first()
            if not tt:
                messages.error(request, "This ticket gift is missing its show.")
                return redirect("rewards:dashboard")

            _fulfill_tickets(account=red.account, ticket_type=tt, qty=red.quantity, redemption=red)
            red.status = "FULFILLED"
            red.fulfilled = True
            red.save(update_fields=["status", "fulfilled"])
            messages.success(request, "Tickets issued! Check your email and Active Tickets.")
            return redirect("rewards:dashboard")

        elif item.fulfill_type == "PRODUCT":
            # If product has variants, send them to choose-variant flow
            from shop.models import Product
            product = None
            if item.target_ct and item.target_ct.model == "product":
                product = Product.objects.filter(pk=item.target_id).first()
            if not product:
                messages.error(request, "This merch gift is missing its product.")
                return redirect("rewards:dashboard")

            if getattr(product, "has_variants", False):
                # Your existing choose_variant flow
                return redirect("rewards:choose_variant", red.id)

            # No variants: fulfill now
            _fulfill_product_without_variant(account=red.account, product=product, qty=red.quantity, redemption=red)
            red.status = "FULFILLED"
            red.fulfilled = True
            red.save(update_fields=["status", "fulfilled"])
            messages.success(request, "Merch redeemed! We created a comp order for you.")
            return redirect("rewards:dashboard")

        else:
            # Custom/simple reward: mark fulfilled
            red.status = "FULFILLED"
            red.fulfilled = True
            red.save(update_fields=["status", "fulfilled"])
            messages.success(request, "Reward redeemed.")
            return redirect("rewards:dashboard")

    except Exception as e:
        messages.error(request, f"Could not redeem: {e}")
        return redirect("rewards:dashboard")
    
def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
            # award signup bonus now
            acc, _ = RewardsAccount.objects.get_or_create(user=user)
            if not acc.signup_bonus_awarded:
                acc.apply_ledger(delta=SIGNUP_BONUS_POINTS, kind="EARN", source="SIGNUP", ref="email-verified")
                acc.signup_bonus_awarded = True
                acc.save(update_fields=["signup_bonus_awarded"])
        login(request, user)
        messages.success(request, "Your email is verified. Welcome! (+10 pts)")
        return redirect("rewards:dashboard")
    else:
        return render(request, "rewards/activation_invalid.html", {})

class ResendActivationForm(forms.Form):
    email = forms.EmailField()

def resend_activation(request):
    form = ResendActivationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            messages.error(request, "If that email exists, we’ve sent a new link.")
            return redirect("rewards:resend_activation")

        if user.is_active:
            messages.info(request, "That account is already active. You can sign in.")
            return redirect("control:accounts:login")

        send_activation_email(user, request=request)
        messages.success(request, "A new activation link has been sent.")
        return redirect("rewards:resend_activation")

    return render(request, "rewards/resend_activation.html", {"form": form})

def terms(request):
    default_email = settings.DEFAULT_FROM_EMAIL
    return render(request, "rewards/terms.html", {
        "default_email": default_email
    })

def privacy(request):
    default_email = settings.DEFAULT_FROM_EMAIL
    return render(request, "rewards/privacy.html", {
        "default_email": default_email
    })


