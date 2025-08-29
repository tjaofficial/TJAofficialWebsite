from typing import Tuple
from django.utils.crypto import get_random_string
from django.utils import timezone
from .models import Order, OrderItem, Product
from .cart_utils import cart_iter_items

def _next_order_number(pk: int) -> str:
    # Simple readable number; you can switch to a dedicated sequence later
    return f"TJA-{pk:06d}"

def create_order_from_cart(request, *, email: str, shipping_method: str, ship_state: str,
                           ship_name: str = "", ship_city: str = "", ship_addr1: str = "", ship_postal: str = "",
                           subtotal_cents: int = 0, shipping_cents: int = 0, tax_cents: int = 0) -> Order:
    total_cents = subtotal_cents + shipping_cents + tax_cents
    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        email=email or "",
        status="pending",
        subtotal_cents=subtotal_cents,
        shipping_cents=shipping_cents,
        tax_cents=tax_cents,
        total_cents=total_cents,
        shipping_method=shipping_method,
        ship_to_name=ship_name,
        ship_to_state=ship_state.upper(),
        ship_to_city=ship_city,
        ship_to_addr1=ship_addr1,
        ship_to_postal=ship_postal,
    )
    # number after pk exists
    order.number = _next_order_number(order.pk)
    order.save(update_fields=["number"])

    # snapshot items
    for p, q in cart_iter_items(request):
        OrderItem.objects.create(
            order=order,
            product=p,
            title_snapshot=p.title,
            price_cents_snapshot=p.price_cents,
            qty=max(1, int(q)),
        )
    return order

def mark_order_paid(order: Order, *, payment_intent: str = ""):
    if order.status != "paid":
        order.status = "paid"
        order.paid_at = timezone.now()
        if payment_intent:
            order.provider_payment_intent = payment_intent
        order.save(update_fields=["status", "paid_at", "provider_payment_intent"])
