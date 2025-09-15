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

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "status", "email", "total_cents", "created_at", "paid_at")
    list_filter = ("status", "created_at")
    search_fields = ("number", "email", "provider_session_id", "provider_payment_intent")
    inlines = [OrderItemInline]

@admin.register(StripeEvent)
class StripeEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "type", "created_at")
    search_fields = ("event_id", "type")
