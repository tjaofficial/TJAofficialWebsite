# cart_utils.py
from typing import Optional
from django.db.models import Sum, F
from django.utils.crypto import get_random_string

from shop.models import Cart, CartItem, Product, ProductVariant


def get_or_create_cart(request) -> Cart:
    """
    One canonical cart for everyone:
      - Auth users: Cart.user=<user>
      - Guests:     Cart.session_key=<request.session.session_key>
    """
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    # ensure session exists
    if not request.session.session_key:
        request.session.save()
    cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart

def cart_count(request) -> int:
    cart = get_or_create_cart(request)
    return cart.items.aggregate(n=Sum("qty"))["n"] or 0

def cart_items_qs(request):
    """Convenience: returns a queryset of CartItem with product/variant joined."""
    cart = get_or_create_cart(request)
    return cart.items.select_related("product", "variant").order_by("added_at")

def cart_subtotal_cents(request) -> int:
    """
    Subtotal should always use the snapshot price on the CartItem line.
    """
    cart = get_or_create_cart(request)
    return (
        cart.items.aggregate(
            c=Sum(F("unit_price_cents") * F("qty"))
        )["c"] or 0
    )

def cart_update_qty(request, *, item_id: int, qty: int) -> int:
    """
    Update a specific CartItem.id quantity and return new total count.
    """
    qty = max(1, int(qty))
    cart = get_or_create_cart(request)
    updated = cart.items.filter(pk=item_id).update(qty=qty)
    # if the item wasn't found, we silently ignore; caller can handle 0 updated
    return cart.items.aggregate(n=Sum("qty"))["n"] or 0

def cart_remove(request, *, item_id: int) -> int:
    """
    Remove a specific CartItem.id and return new total count.
    """
    cart = get_or_create_cart(request)
    cart.items.filter(pk=item_id).delete()
    return cart.items.aggregate(n=Sum("qty"))["n"] or 0

def cart_clear(request) -> None:
    """
    Clear the entire cart (this cart only).
    """
    cart = get_or_create_cart(request)
    cart.items.all().delete()

# --- Optional: legacy session merge (if you ever had session dict carts) ---

def merge_session_into_user_cart(request, user):
    """
    If you previously stored a session dict cart like {"<product_id>": qty},
    merge those into the user's DB cart and clear the session dict.
    """
    sess = request.session.get("cart", {})
    if not sess:
        return
    cart, _ = Cart.objects.get_or_create(user=user)

    for pid, qty in sess.items():
        try:
            p = Product.objects.get(pk=int(pid), is_active=True)
        except Product.DoesNotExist:
            continue

        # No-variant legacy lines: merge into (product, variant=None)
        item, _ = CartItem.objects.get_or_create(
            cart=cart, product=p, variant=None, defaults={"qty": 0, "unit_price_cents": p.price_cents}
        )
        item.qty += max(1, int(qty))
        item.save()

    request.session["cart"] = {}
    request.session.modified = True
