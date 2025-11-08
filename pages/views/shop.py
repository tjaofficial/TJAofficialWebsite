from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_POST
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Q, Sum
from shop.models import Product, Order, OrderItem, StripeEvent, CartItem, ProductVariant, Cart
from django.shortcuts import render, get_object_or_404
from ..cart_utils import (
    cart_items_qs, cart_subtotal_cents, cart_remove, cart_clear, cart_count as cart_count_val
)
from decimal import Decimal, ROUND_HALF_UP
from ..order_utils import create_order_from_cart, mark_order_paid
from django.db.models import F
from coreutils.mailer import send_notification_update
from django.conf import settings

def shop(request):
    q = (request.GET.get("q") or "").strip()
    products = Product.objects.filter(is_active=True)
    if q:
        products = products.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q)
        )
    products = products[:200]  # simple cap
    # Ensure session exists (prepping for cart)
    get_token(request)
    return render(request, "pages/shop.html", {"products": products, "query": q})

@transaction.atomic
def add_to_cart(request, slug):
    if request.method != 'POST':
        return redirect('product_detail', slug=slug)

    product = get_object_or_404(Product, slug=slug, is_active=True)
    try:
        qty = max(1, int(request.POST.get('qty', 1)))
    except Exception:
        qty = 1

    # Resolve variant (if required)
    variant = None
    if product.has_variants:
        variant_id = request.POST.get('variant_id')
        if not variant_id:
            # Optional convenience: auto-pick if exactly one in-stock variant exists
            qs = product.variants.filter(is_active=True, inventory__gt=0)
            if qs.count() == 1:
                variant = qs.first()
            else:
                return JsonResponse({'ok': False, 'error': 'Please choose a size'}, status=400)
        else:
            variant = get_object_or_404(ProductVariant, pk=variant_id, product=product, is_active=True)
        if variant.inventory <= 0:
            return JsonResponse({'ok': False, 'error': 'That size is out of stock'}, status=400)
        unit_price = variant.price_cents
    else:
        if product.inventory <= 0:
            return JsonResponse({'ok': False, 'error': 'Out of stock'}, status=400)
        unit_price = product.price_cents

    cart = get_or_create_cart(request)

    # IMPORTANT: merge by (cart, product, variant). This avoids unique-constraint IntegrityError.
    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, variant=variant,
        defaults={'qty': 0, 'unit_price_cents': unit_price},
    )

    # Keep the first captured unit price; or, if you prefer, update to current price:
    if created and item.unit_price_cents == 0:
        item.unit_price_cents = unit_price

    # Atomic increment
    CartItem.objects.filter(pk=item.pk).update(qty=F('qty') + qty)
    item.refresh_from_db(fields=['qty'])

    count = cart.items.aggregate(Sum('qty'))['qty__sum'] or 0
    return JsonResponse({'ok': True, 'cart_count': count})

def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.save()
        cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart

def cart_count(request):
    return JsonResponse({"count": cart_count_val(request)})

def _cart_dict(request):
    return request.session.get("cart", {})

def _cart_items(request):
    """
    Returns a list of dicts:
      {product, qty, line_cents}
    and totals in cents.
    """
    cart = _cart_dict(request)
    ids = [int(pid) for pid in cart.keys()]
    products = {p.id: p for p in Product.objects.filter(id__in=ids, is_active=True)}
    items, subtotal = [], 0
    for pid, qty in cart.items():
        pid_int = int(pid)
        p = products.get(pid_int)
        if not p: 
            continue
        q = max(1, int(qty))
        line = p.price_cents * q
        subtotal += line
        items.append({"product": p, "qty": q, "line_cents": line})
    return items, subtotal

def _cart_items_and_subtotal(request):
    """
    Return a list of dicts:
      {product, variant, qty, unit_cents, line_cents}
    plus subtotal in cents.
    """
    items = []
    subtotal = 0
    for it in cart_items_qs(request):
        line = it.unit_price_cents * it.qty
        subtotal += line
        items.append({
            "product": it.product,
            "variant": it.variant,
            "qty": it.qty,
            "unit_cents": it.unit_price_cents,
            "line_cents": line,
        })
    return items, subtotal

def cart(request):
    cart = get_or_create_cart(request)
    items = (cart.items
             .select_related('product','variant')
             .order_by('added_at'))

    # subtotal in cents using the snapshot price
    subtotal = items.aggregate(
        c=Sum(F('unit_price_cents') * F('qty'))
    )['c'] or 0

    return render(request, "pages/cart.html", {
        "items": items,
        "subtotal_cents": subtotal,
        "subtotal_display": f"${subtotal/100:.2f}",
    })

def cart_update(request):
    try:
        item_id = int(request.POST.get("item_id"))
        qty = max(1, int(request.POST.get("qty", "1")))
    except Exception:
        return HttpResponseBadRequest("bad params")

    cart = get_or_create_cart(request)
    # Only allow touching items in this cart
    updated = (cart.items.filter(pk=item_id)
              .update(qty=qty))
    if not updated:
        return HttpResponseBadRequest("not found")

    subtotal = cart.items.aggregate(c=Sum(F('unit_price_cents') * F('qty')))['c'] or 0
    count = cart.items.aggregate(c=Sum('qty'))['c'] or 0
    return JsonResponse({"ok": True, "count": count, "subtotal": f"${subtotal/100:.2f}"})

@require_POST
def cart_remove(request):
    try:
        item_id = int(request.POST.get("item_id"))
    except Exception:
        return HttpResponseBadRequest("bad params")

    cart = get_or_create_cart(request)
    cart.items.filter(pk=item_id).delete()
    subtotal = cart.items.aggregate(c=Sum(F('unit_price_cents') * F('qty')))['c'] or 0
    count = cart.items.aggregate(c=Sum('qty'))['c'] or 0
    return JsonResponse({"ok": True, "count": count, "subtotal": f"${subtotal/100:.2f}"})

@require_POST
def cart_clear(request):
    cart_clear(request)
    return JsonResponse({"ok": True, "count": 0, "subtotal": "$0.00"})

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)

    # normalize images -> list of {"url","alt"}
    imgs = []
    for im in product.images.all():
        try:
            url = im.image.url
        except Exception:
            url = ""
        if url:
            imgs.append({"url": url, "alt": getattr(im, "alt", "") or product.title})
    if not imgs and product.image_url:
        imgs = [{"url": product.image_url, "alt": product.title}]

    variants = []
    if product.has_variants:
        variants = product.variants.filter(is_active=True).order_by("size")

    related = product.related() if hasattr(product, "related") else []

    return render(request, "pages/product_detail.html", {
        "product": product,
        "images": imgs,
        "variants": variants,
        "related": related,
    })

# Simple shipping table (cents)
SHIPPING_METHODS = {
    "standard": {"label": "Standard (5–7 business days)", "amount_cents": 599},
    "express":  {"label": "Express (2–3 business days)",  "amount_cents": 1499},
    "overnight":{"label": "Overnight (1 business day)",   "amount_cents": 2999},
}
DEFAULT_SHIP = "standard"

# Very simple tax: 6% if MI, otherwise 0%
def _tax_rate_for_state(state_code: str) -> Decimal:
    if (state_code or "").strip().upper() == "MI":
        return Decimal("0.06")
    return Decimal("0.00")

@require_POST
def cart_quote(request):
    method = request.POST.get("method", DEFAULT_SHIP)
    state = request.POST.get("state", "")
    if method not in SHIPPING_METHODS:
        return HttpResponseBadRequest("bad shipping method")

    items, subtotal = _cart_items_and_subtotal(request)
    ship_cents = SHIPPING_METHODS[method]["amount_cents"]
    tax_rate = _tax_rate_for_state(state)
    # tax on (subtotal + shipping)
    tax_cents = int((Decimal(subtotal + ship_cents) * tax_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    total_cents = subtotal + ship_cents + tax_cents

    return JsonResponse({
        "ok": True,
        "subtotal_cents": subtotal, "ship_cents": ship_cents,
        "tax_cents": tax_cents, "total_cents": total_cents,
        "subtotal": f"${subtotal/100:.2f}",
        "ship": f"${ship_cents/100:.2f}",
        "tax": f"${tax_cents/100:.2f}",
        "total": f"${total_cents/100:.2f}",
    })

def checkout(request):
    items, subtotal = _cart_items_and_subtotal(request)
    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        email="tjaofficial@gmail.com",  # set as appropriate
        total_cents=0,
    )

    total = 0
    cart = get_or_create_cart(request)
    for it in cart.items.select_related('product', 'variant'):
        OrderItem.objects.create(
            order=order,
            product=it.product,
            variant=it.variant,
            title_snapshot=it.product.title,
            size=(it.variant.size if it.variant else ""),
            qty=it.qty,
            price_cents_snapshot=it.unit_price_cents,
        )
        total += it.unit_price_cents * it.qty

    order.total_cents = total
    order.save()
    return render(request, "pages/checkout.html", {
        "items": items,
        "subtotal_cents": subtotal,
        "subtotal_display": f"${subtotal/100:.2f}",
        "shipping_methods": SHIPPING_METHODS,
        "default_method": DEFAULT_SHIP,
    })

@require_POST
def checkout_start(request):
    method = request.POST.get("method", DEFAULT_SHIP)
    state = (request.POST.get("state") or "").upper()
    email = (request.POST.get("email") or "").strip()
    if method not in SHIPPING_METHODS:
        return redirect("checkout")

    # --- Cart snapshot (variant-aware) ---
    lines = list(cart_items_qs(request))  # CartItem objects
    if not lines:
        return redirect("cart")

    subtotal = cart_subtotal_cents(request)
    ship_cents = SHIPPING_METHODS[method]["amount_cents"]
    tax_rate = _tax_rate_for_state(state)
    tax_cents = int((Decimal(subtotal + ship_cents) * tax_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    total_cents = subtotal + ship_cents + tax_cents

    # --- Create Order from cart lines (captures unit_price + size) ---
    order = create_order_from_cart(
        request,
        email=email,
        shipping_method=method,
        ship_state=state,
        subtotal_cents=subtotal,
        shipping_cents=ship_cents,
        tax_cents=tax_cents,
    )

    # --- Build Stripe line_items from CartItem.unit_price_cents ---
    import os, stripe
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe.api_key:
        return HttpResponseBadRequest("Stripe not configured")

    line_items = []
    for it in lines:
        name = it.product.title
        if it.variant and getattr(it.variant, "size", ""):
            name = f"{name} — {it.variant.size}"
        line_items.append({
            "price_data": {
                "currency": "usd",
                "product_data": {"name": name},
                "unit_amount": int(it.unit_price_cents),
            },
            "quantity": int(it.qty),
        })

    # Add shipping + tax as separate line items (simple path; or use Stripe Tax & Shipping Options)
    if ship_cents:
        line_items.append({
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"Shipping: {SHIPPING_METHODS[method]['label']}"},
                "unit_amount": int(ship_cents),
            },
            "quantity": 1,
        })
    if tax_cents:
        line_items.append({
            "price_data": {
                "currency": "usd",
                "product_data": {"name": "Estimated tax"},
                "unit_amount": int(tax_cents),
            },
            "quantity": 1,
        })

    # Attach metadata so webhook can find the order
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=line_items,
        success_url=request.build_absolute_uri("/checkout/success/"),
        cancel_url=request.build_absolute_uri("/checkout/"),
        metadata={"order_id": str(order.id)},
    )

    # Persist provider session id on the order (optional but handy)
    try:
        order.payment_provider = "stripe"
        order.provider_session_id = session.id
        order.total_cents = total_cents
        order.save(update_fields=["payment_provider", "provider_session_id", "total_cents"])
    except Exception:
        pass

    return redirect(session.url)

def checkout_success(request):
    cart_clear(request)
    return render(request, "pages/checkout_success.html")

def checkout_cancel(request):
    return render(request, "pages/checkout_cancel.html")

@csrf_exempt
def stripe_webhook(request):
    # Set STRIPE_WEBHOOK_SECRET in .env when you go live
    import json, os
    try:
        import stripe
    except Exception:
        return HttpResponse(status=200)  # allow noop in dev without stripe

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET_SHOP
    if not webhook_secret:
        return HttpResponse(status=200)  # no secret configured yet
    try:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=webhook_secret)
    except Exception:
        return HttpResponseBadRequest("invalid signature")

    # Idempotency
    if StripeEvent.objects.filter(event_id=event["id"]).exists():
        return HttpResponse(status=200)
    StripeEvent.objects.create(event_id=event["id"], type=event["type"])

    # Handle a few key event types
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session.get("id")
        order_id = session.get("metadata", {}).get("order_id")
        payment_intent = session.get("payment_intent")

        try:
            if order_id:
                order = Order.objects.get(pk=order_id)
            else:
                order = Order.objects.get(provider_session_id=session_id)
        except Order.DoesNotExist:
            return HttpResponse(status=200)

        if order.status != "paid":
            with transaction.atomic():
                # Mark paid
                mark_order_paid(order, payment_intent=payment_intent)
                send_notification_update("order", order, request=request)
                # Decrement inventory
                for it in order.items.select_related("product"):
                    Product.objects.filter(pk=it.product_id).update(inventory=F("inventory") - it.qty)
                # (optional) clear cart for that user/session is not straightforward from webhook request;
                # you can leave it to success page or use fulfillment email.
    elif event["type"] == "payment_intent.succeeded":
        # Optional: cross-check order by payment intent if you saved it earlier
        pass
    # ---------- ABANDONED/CANCELED ----------
    elif event["type"] in ("checkout.session.expired", "checkout.session.async_payment_failed"):
        session = event["data"]["object"]
        session_id = session.get("id")

        order = Order.objects.filter(provider_session_id=session_id).first()
        if order and order.status not in ("paid", "refunded", "canceled", "failed"):
            # expired = customer never completed; async_payment_failed = later failure
            order.status = "canceled" if event["type"] == "checkout.session.expired" else "failed"
            order.save(update_fields=["status"])
    # ---------- CARD DECLINED / FAILED INTENT (best-effort) ----------
    elif event["type"] == "payment_intent.payment_failed":
        pi = event["data"]["object"]
        intent_id = pi.get("id")
        # We only know the order if we had stored provider_payment_intent previously.
        # (Often we only set this on 'paid', so this may be a no-op—but it’s safe.)
        order = Order.objects.filter(provider_payment_intent=intent_id).first()
        if order and order.status not in ("paid", "refunded", "canceled", "failed"):
            order.status = "failed"
            order.save(update_fields=["status"])

    return HttpResponse(status=200)