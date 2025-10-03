from django.contrib import admin
from .models import *
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

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "email", "status", "total_cents", "paid_at")
    search_fields = ("number", "email", "provider_payment_intent")
    list_filter = ("status", "payment_provider", "created_at", "paid_at")
    date_hierarchy = "created_at"
    actions = [mark_as_shipped]

@admin.register(StripeEvent)
class StripeEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "type", "created_at")
    search_fields = ("event_id", "type")
