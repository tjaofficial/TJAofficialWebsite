from typing import Iterator, List, Tuple
from django.db.models import Sum
from .models import Cart, CartItem, Product

def _get_or_create_user_cart(user) -> Cart:
    cart, _ = Cart.objects.get_or_create(user=user, active=True)
    return cart

def merge_session_into_user_cart(request, user):
    sess = request.session.get("cart", {})
    if not sess:
        return
    cart = _get_or_create_user_cart(user)
    for pid, qty in sess.items():
        try:
            p = Product.objects.get(pk=int(pid), is_active=True)
        except Product.DoesNotExist:
            continue
        item, _ = CartItem.objects.get_or_create(cart=cart, product=p, defaults={"qty": 0})
        item.qty += max(1, int(qty))
        item.save()
    request.session["cart"] = {}
    request.session.modified = True

def cart_add(request, product: Product, qty: int) -> int:
    qty = max(1, int(qty))
    if request.user.is_authenticated:
        cart = _get_or_create_user_cart(request.user)
        item, _ = CartItem.objects.get_or_create(cart=cart, product=product, defaults={"qty": 0})
        item.qty += qty
        item.save()
        return CartItem.objects.filter(cart=cart).aggregate(n=Sum("qty"))["n"] or 0
    # guests -> session
    sess = request.session.get("cart", {})
    k = str(product.id)
    sess[k] = int(sess.get(k, 0)) + qty
    request.session["cart"] = sess
    request.session.modified = True
    return sum(sess.values())

def cart_update_qty(request, product_id: int, qty: int) -> int:
    qty = max(1, int(qty))
    if request.user.is_authenticated:
        cart = _get_or_create_user_cart(request.user)
        item, _ = CartItem.objects.get_or_create(cart=cart, product_id=product_id, defaults={"qty": 0})
        item.qty = qty
        item.save()
        return CartItem.objects.filter(cart=cart).aggregate(n=Sum("qty"))["n"] or 0
    sess = request.session.get("cart", {})
    sess[str(product_id)] = qty
    request.session["cart"] = sess
    request.session.modified = True
    return sum(sess.values())

def cart_remove(request, product_id: int) -> int:
    if request.user.is_authenticated:
        cart = _get_or_create_user_cart(request.user)
        CartItem.objects.filter(cart=cart, product_id=product_id).delete()
        return CartItem.objects.filter(cart=cart).aggregate(n=Sum("qty"))["n"] or 0
    sess = request.session.get("cart", {})
    sess.pop(str(product_id), None)
    request.session["cart"] = sess
    request.session.modified = True
    return sum(sess.values())

def cart_clear(request):
    if request.user.is_authenticated:
        cart = _get_or_create_user_cart(request.user)
        cart.items.all().delete()
    request.session["cart"] = {}
    request.session.modified = True

def cart_count(request) -> int:
    if request.user.is_authenticated:
        cart = _get_or_create_user_cart(request.user)
        return CartItem.objects.filter(cart=cart).aggregate(n=Sum("qty"))["n"] or 0
    return sum(request.session.get("cart", {}).values())

def cart_iter_items(request) -> Iterator[Tuple[Product, int]]:
    if request.user.is_authenticated:
        cart = _get_or_create_user_cart(request.user)
        for it in cart.items.select_related("product"):
            if it.product.is_active:
                yield it.product, int(it.qty)
    else:
        sess = request.session.get("cart", {})
        ids = [int(k) for k in sess.keys()]
        prods = {p.id: p for p in Product.objects.filter(id__in=ids, is_active=True)}
        for k, q in sess.items():
            p = prods.get(int(k))
            if p:
                yield p, int(q)
