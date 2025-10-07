from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Sum, F, ExpressionWrapper, BigIntegerField
from .models import (
    Order, OrderItem, Product, ProductImage, Coupon
)
from .forms import ProductForm, CouponForm, TokenIssueForm
from django.http import HttpResponse
import csv
from django.contrib import messages
from django.utils import timezone
from .services import send_order_shipped_email

is_super = user_passes_test(lambda u: u.is_superuser)

# ---------- ORDERS ----------
@is_super
def orders_list(request):
    qs = Order.objects.all().order_by("-created_at")

    email  = request.GET.get("email", "").strip()
    number = request.GET.get("number", "").strip()
    status = request.GET.get("status", "").strip()
    state  = request.GET.get("state", "").strip()

    if not status:
        status = "paid"

    if email:
        qs = qs.filter(Q(email__icontains=email) | Q(user__email__icontains=email))
    if number:
        qs = qs.filter(number__icontains=number)
    if status:
        qs = qs.filter(status=status)
    if state:
        qs = qs.filter(ship_to_state__iexact=state)

    ctx = {"orders": qs, "status_choices": Order.STATUS_CHOICES}
    return render(request, "shop/orders_list.html", ctx)

@is_super
def order_detail(request, number):
    order = get_object_or_404(Order.objects.prefetch_related("items"), number=number)
    return render(request, "shop/order_detail.html", {"order": order})

# ---------- INVENTORY / SALES REPORT ----------
@is_super
def inventory_report(request):
    """
    Filters:
      - title (matches OrderItem.title_snapshot)
      - size (OrderItem.size)
      - buyer (Order.ship_to_name)
      - state (Order.ship_to_state)
      - date range (Order.created_at date)
    """
    title = request.GET.get("title", "").strip()
    size = request.GET.get("size", "").strip()
    buyer = request.GET.get("buyer", "").strip()
    state = request.GET.get("state", "").strip()
    date_from = request.GET.get("from", "").strip()
    date_to = request.GET.get("to", "").strip()

    items = (OrderItem.objects
        .select_related("order", "product")
        .filter(order__status="paid")
        .order_by("-order__created_at"))

    if title:
        items = items.filter(title_snapshot__icontains=title)
    if size:
        items = items.filter(size__icontains=size)
    if buyer:
        items = items.filter(order__ship_to_name__icontains=buyer)
    if state:
        items = items.filter(order__ship_to_state__iexact=state)
    if date_from:
        items = items.filter(order__created_at__date__gte=date_from)
    if date_to:
        items = items.filter(order__created_at__date__lte=date_to)

    items_with_total = items.annotate(
        line_total=ExpressionWrapper(
            F("qty") * F("price_cents_snapshot"),
            output_field=BigIntegerField()
        )
    )

    by_product = (
        items_with_total
        .values("title_snapshot")
        .annotate(
            qty=Sum("qty"),
            revenue=Sum("line_total")
        )
        .order_by("-revenue")
    )

    return render(request, "shop/inventory.html", {
        "items": items[:500],
        "by_product": by_product,
        "q": {"title": title, "size": size, "buyer": buyer, "state": state,
              "from": date_from, "to": date_to}
    })

# ---------- PRODUCTS ----------
@is_super
def product_add(request):
    """
    Create a simple product (no variants required).
    You can upload the main image in Product, and optionally multiple extra images.
    """
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            # Extra images (optional)
            for i, f in enumerate(request.FILES.getlist("extra_images")):
                ProductImage.objects.create(product=product, image=f, sort=i)
            return redirect("control:shop:inventory")
    else:
        form = ProductForm()
    return render(request, "shop/product_add.html", {"form": form})

# ---------- COUPONS ----------
@is_super
def coupons_list(request):
    qs = Coupon.objects.all().order_by("-id")
    return render(request, "shop/coupons_list.html", {"coupons": qs})

@is_super
def coupon_new(request):
    form = CouponForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("control:shop:coupons")
    return render(request, "shop/coupon_form.html", {"form": form, "mode": "new"})

@is_super
def coupon_edit(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    form = CouponForm(request.POST or None, instance=coupon)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("control:shop:coupons")
    return render(request, "shop/coupon_form.html", {"form": form, "mode": "edit", "coupon": coupon})

@is_super
def issue_token(request):
    form = TokenIssueForm(request.POST or None)
    token = None
    if request.method == "POST" and form.is_valid():
        token = form.save()
    return render(request, "shop/issue_token.html", {"form": form, "token": token})

# ---------- BUDGET / SALES ----------
@is_super
def budget_sales(request):
    """
    Filters orders by date and state, then computes:
    - Totals: revenue, shipping, tax, discounts, net
    - By product: qty + revenue
    - By state: revenue
    - By day: revenue
    """
    date_from = request.GET.get("from", "").strip()
    date_to   = request.GET.get("to", "").strip()
    state     = request.GET.get("state", "").strip()

    orders = Order.objects.filter(status="paid")

    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    if state:
        orders = orders.filter(ship_to_state__iexact=state)

    # Totals (cents)
    totals = orders.aggregate(
        revenue=Sum("total_cents"),
        shipping=Sum("shipping_cents"),
        tax=Sum("tax_cents"),
        discount=Sum("subtotal_cents") - Sum("total_cents") - Sum("shipping_cents") - Sum("tax_cents")
        # optional: if you store discount separately, swap this for Sum("discount_cents")
    )

    # Guard against None
    rev = totals.get("revenue") or 0
    ship = totals.get("shipping") or 0
    tax  = totals.get("tax") or 0
    disc = totals.get("discount") or 0  # if you switch to Sum("discount_cents"), keep same name

    net = rev - ship - tax - disc

    # Items filtered by the same order set
    items = (OrderItem.objects
             .select_related("order")
             .filter(order__in=orders))

    items = items.annotate(
        line_total=ExpressionWrapper(
            F("qty") * F("price_cents_snapshot"),
            output_field=BigIntegerField()
        )
    )

    # By product
    by_product = (
        items.values("title_snapshot")
             .annotate(qty=Sum("qty"), revenue=Sum("line_total"))
             .order_by("-revenue")
    )

    # By state
    by_state = (
        orders.values("ship_to_state")
              .annotate(revenue=Sum("total_cents"))
              .order_by("-revenue")
    )

    # By day
    by_day = (
        orders.values("created_at__date")
              .annotate(revenue=Sum("total_cents"))
              .order_by("created_at__date")
    )

    ctx = {
        "q": {"from": date_from, "to": date_to, "state": state},
        "totals": totals,
        "by_product": by_product,
        "by_state": by_state,
        "by_day": by_day,
        "net": net,
    }
    return render(request, "shop/budget.html", ctx)


@is_super
def budget_export_csv(request):
    """Export the filtered OrderItem dataset (with line totals) as CSV."""
    date_from = request.GET.get("from", "").strip()
    date_to   = request.GET.get("to", "").strip()
    state     = request.GET.get("state", "").strip()

    orders = Order.objects.all()
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    if state:
        orders = orders.filter(ship_to_state__iexact=state)

    items = (OrderItem.objects
             .select_related("order", "product")
             .filter(order__in=orders)
             .annotate(line_total=ExpressionWrapper(
                 F("qty") * F("price_cents_snapshot"),
                 output_field=BigIntegerField()
             )))

    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = "attachment; filename=budget_export.csv"
    writer = csv.writer(resp)
    writer.writerow(["date", "order_number", "title", "size", "qty", "unit_cents", "line_cents", "state"])

    for it in items.order_by("order__created_at"):
        writer.writerow([
            it.order.created_at.strftime("%Y-%m-%d %H:%M"),
            it.order.number,
            it.title_snapshot,
            it.size,
            it.qty,
            it.price_cents_snapshot,
            it.line_total,
            it.order.ship_to_state,
        ])

    return resp

@is_super
def mark_order_shipped(request, pk):
    o = get_object_or_404(Order, pk=pk)
    o.status = "fulfilled"
    if hasattr(o, "shipped_at") and not o.shipped_at:
        o.shipped_at = timezone.now()
    o.save(update_fields=["status"] + (["shipped_at"] if hasattr(o, "shipped_at") else []))
    try:
        send_order_shipped_email(o, request=request)
        messages.success(request, f"Order {o.number or o.pk} marked as shipped and email sent.")
    except Exception as e:
        messages.warning(request, f"Order marked shipped, but email failed: {e}")
    return redirect(request.META.get("HTTP_REFERER", "/"))


