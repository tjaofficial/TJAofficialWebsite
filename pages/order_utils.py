from django.db import transaction
from django.utils.crypto import get_random_string
from django.utils import timezone
from shop.models import Order, OrderItem
from .cart_utils import cart_items_qs, cart_subtotal_cents

def _next_order_number(pk: int) -> str:
    # Simple readable number; you can switch to a dedicated sequence later
    return f"TJA-{pk:06d}"

def create_order_from_cart(
    request, *,
    email: str,
    shipping_method: str,
    ship_state: str,
    ship_name: str = "",
    ship_city: str = "",
    ship_addr1: str = "",
    ship_postal: str = "",
    subtotal_cents: int = 0,
    shipping_cents: int = 0,
    tax_cents: int = 0,
) -> Order:
    """
    Snapshot current cart lines into an Order + OrderItems.
    Uses CartItem.unit_price_cents and CartItem.variant (size) if present.
    """
    # If caller didn’t precompute subtotal, compute from CartItem lines
    if not subtotal_cents:
        subtotal_cents = cart_subtotal_cents(request)

    total_cents = subtotal_cents + shipping_cents + tax_cents

    with transaction.atomic():
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
            ship_to_state=(ship_state or "").upper(),
            ship_to_city=ship_city,
            ship_to_addr1=ship_addr1,
            ship_to_postal=ship_postal,
        )
        # assign human order number after pk exists
        order.number = _next_order_number(order.pk)
        order.save(update_fields=["number"])

        # Build OrderItems from CartItem snapshot
        oi_fields = {f.name for f in OrderItem._meta.get_fields()}

        for it in cart_items_qs(request):  # it = CartItem
            fields = {
                "order": order,
                "product": it.product,
                "qty": int(it.qty),
            }
            # variant if model supports it
            if "variant" in oi_fields:
                fields["variant"] = it.variant

            # title snapshot (supports either 'title' or 'title_snapshot')
            title_val = getattr(it.product, "title", "")
            if "title" in oi_fields:
                fields["title"] = title_val
            elif "title_snapshot" in oi_fields:
                fields["title_snapshot"] = title_val

            # size snapshot if schema has 'size' and there is a variant
            if "size" in oi_fields:
                fields["size"] = (it.variant.size if it.variant else "")

            # price snapshot (supports either 'unit_price_cents' or 'price_cents_snapshot')
            price_val = int(it.unit_price_cents)
            if "unit_price_cents" in oi_fields:
                fields["unit_price_cents"] = price_val
            elif "price_cents_snapshot" in oi_fields:
                fields["price_cents_snapshot"] = price_val

            OrderItem.objects.create(**fields)

    return order

def mark_order_paid(order: Order, *, payment_intent: str = ""):
    if order.status != "paid":
        order.status = "paid"
        order.paid_at = timezone.now()
        if payment_intent:
            order.provider_payment_intent = payment_intent
        order.save(update_fields=["status", "paid_at", "provider_payment_intent"])
