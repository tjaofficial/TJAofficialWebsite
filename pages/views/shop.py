from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_POST
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Q
from ..models import Product, Order, OrderItem, StripeEvent
from django.shortcuts import render, get_object_or_404
from ..cart_utils import (
    cart_add, cart_update_qty, cart_remove, cart_clear, cart_count as cart_count_val, cart_iter_items
)
from decimal import Decimal, ROUND_HALF_UP
from ..order_utils import create_order_from_cart, mark_order_paid
from django.db.models import F

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

@require_POST
def add_to_cart(request):
    pid = request.POST.get("product_id"); qty = int(request.POST.get("qty", "1"))
    product = Product.objects.get(pk=pid, is_active=True)
    count = cart_add(request, product, qty)
    return JsonResponse({"ok": True, "product": {"id": product.id, "title": product.title}, "cart_count": count})

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
    items, subtotal = [], 0
    for p, q in cart_iter_items(request):
        line = p.price_cents * q
        subtotal += line
        items.append({"product": p, "qty": q, "line_cents": line})
    return items, subtotal

def cart(request):
    items, subtotal = _cart_items_and_subtotal(request)
    return render(request, "pages/cart.html", {
        "items": items, "subtotal_cents": subtotal, "subtotal_display": f"${subtotal/100:.2f}",
    })

@require_POST
def cart_update(request):
    pid = int(request.POST.get("product_id")); qty = int(request.POST.get("qty", "1"))
    cart_update_qty(request, pid, qty)
    _, subtotal = _cart_items_and_subtotal(request)
    return JsonResponse({"ok": True, "count": cart_count_val(request), "subtotal": f"${subtotal/100:.2f}"})

@require_POST
def cart_remove(request):
    pid = int(request.POST.get("product_id"))
    cart_remove(request, pid)
    _, subtotal = _cart_items_and_subtotal(request)
    return JsonResponse({"ok": True, "count": cart_count_val(request), "subtotal": f"${subtotal/100:.2f}"})

@require_POST
def cart_clear(request):
    cart_clear(request)
    return JsonResponse({"ok": True, "count": 0, "subtotal": "$0.00"})

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    images = list(product.images.all())
    if not images and product.image_url:
        # fallback to primary image as a pseudo gallery slot
        images = [{"url": product.image_url, "alt": product.title}]
    related = product.related()
    return render(request, "pages/product_detail.html", {
        "p": product, 
        "images": images, 
        "related": related
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

    # compute totals
    items, subtotal = _cart_items_and_subtotal(request)
    if not items:
        return redirect("cart")
    ship_cents = SHIPPING_METHODS[method]["amount_cents"]
    tax_rate = _tax_rate_for_state(state)
    tax_cents = int((Decimal(subtotal + ship_cents) * tax_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    # create Order (pending)
    order = create_order_from_cart(
        request,
        email=email,
        shipping_method=method,
        ship_state=state,
        subtotal_cents=subtotal,
        shipping_cents=ship_cents,
        tax_cents=tax_cents,
    )

    # ---- Stripe: uncomment when ready ----
    import stripe, os
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
    line_items = [
      {"price_data": {"currency": "usd",
                      "product_data": {"name": it["product"].title},
                      "unit_amount": it["product"].price_cents},
       "quantity": it["qty"]} for it in items
    ]
    # Add shipping + tax as extra line items (or use Stripe's tax/shipping features)
    if ship_cents:
        line_items.append({"price_data":{"currency":"usd","product_data":{"name":f"Shipping: {SHIPPING_METHODS[method]['label']}"},"unit_amount": ship_cents},"quantity":1})
    if tax_cents:
        line_items.append({"price_data":{"currency":"usd","product_data":{"name":"Estimated tax"},"unit_amount": tax_cents},"quantity":1})
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=line_items,
        success_url=request.build_absolute_uri("/checkout/success/"),
        cancel_url=request.build_absolute_uri("/checkout/"),
    )
    return redirect(session.url)

    # #Placeholder redirect (fake success)
    # return redirect("checkout")

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
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
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
                # Decrement inventory
                for it in order.items.select_related("product"):
                    Product.objects.filter(pk=it.product_id).update(inventory=F("inventory") - it.qty)
                # (optional) clear cart for that user/session is not straightforward from webhook request;
                # you can leave it to success page or use fulfillment email.

    elif event["type"] == "payment_intent.succeeded":
        # Optional: cross-check order by payment intent if you saved it earlier
        pass

    return HttpResponse(status=200)