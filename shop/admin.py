from django.contrib import admin, messages
from .models import *
from rewards.models import PurchaseRecord
from rewards.utils import record_store_order
from django.utils import timezone
# Register your models here.

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("title_snapshot", "price_cents_snapshot", "qty")
    
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('size', 'price_cents', 'inventory', 'is_active', 'sku')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'has_variants', 'price_cents', 'inventory')
    list_filter = ('is_active', 'has_variants', 'category')
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ProductVariantInline]

admin.site.register(Category)
admin.site.register(ProductImage)
admin.site.register(Cart)
admin.site.register(CartItem)

@admin.action(description="Mark as shipped (fulfilled)")
def mark_as_shipped(modeladmin, request, queryset):
    # If you added shipped_at field (see below), set it too
    now = timezone.now()
    for o in queryset:
        o.status = "fulfilled"
        if hasattr(o, "shipped_at") and not o.shipped_at:
            o.shipped_at = now
        o.save(update_fields=["status"] + (["shipped_at"] if hasattr(o, "shipped_at") else []))

@admin.action(description="Force PAID + Sync to Rewards")
def force_paid_and_sync(modeladmin, request, queryset):
    created = skipped = 0
    for o in queryset:
        # Force to paid if not already
        if o.status != "paid":
            o.status = "paid"
            o.paid_at = timezone.now()
            if not o.payment_provider:
                o.payment_provider = "stripe"
            o.save(update_fields=["status", "paid_at", "payment_provider"])

        # Create PurchaseRecord if missing
        ref = o.number or str(o.pk)
        if PurchaseRecord.objects.filter(kind="ORDER", external_id=ref).exists():
            skipped += 1
            continue

        user = o.user if getattr(o, "user_id", None) else None
        email = (None if user else (o.email or "")) or ""
        meta = {
            "number": o.number,
            "shipping_cents": o.shipping_cents,
            "tax_cents": o.tax_cents,
            "total_cents": o.total_cents,
            "ship": {
                "name": o.ship_to_name, "addr1": o.ship_to_addr1, "city": o.ship_to_city,
                "state": o.ship_to_state, "postal": o.ship_to_postal, "method": o.shipping_method,
            },
            "payment": {
                "provider": o.payment_provider,
                "session_id": o.provider_session_id,
                "payment_intent": o.provider_payment_intent,
            },
        }
        record_store_order(
            order_id=ref,
            subtotal_cents=int(getattr(o, "subtotal_cents", 0)) or 0,
            currency="USD",
            user=user,
            email=email,
            phone=None,
            meta=meta,
        )
        created += 1

    messages.success(request, f"Forced PAID + synced. Created: {created}, skipped: {skipped}")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "email", "status", "total_cents", "paid_at", "paid_at", "provider_session_id", "provider_payment_intent")
    search_fields = ("number", "email", "provider_payment_intent", "provider_session_id")
    list_filter = ("status", "payment_provider", "created_at", "paid_at")
    date_hierarchy = "created_at"
    actions = [mark_as_shipped, force_paid_and_sync]

@admin.register(StripeEvent)
class StripeEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "type", "created_at")
    search_fields = ("event_id", "type")



