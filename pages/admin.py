from django.contrib import admin
from .models import *
from django.http import HttpResponse
import csv

# Register your models here.

admin.site.register(Show)

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
class TrackInline(admin.TabularInline):
    model = Track
    extra = 0

@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = ("title", "release_type", "release_date")
    list_filter = ("release_type", "release_date")
    search_fields = ("title",)
    inlines = [TrackInline]
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("title_snapshot", "price_cents_snapshot", "qty")

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

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "published_at", "is_public", "sort")
    list_filter = ("is_public",)
    search_fields = ("title", "youtube_url")

@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "source", "created_at", "confirmed_at")
    search_fields = ("email", "name", "source")
    list_filter = ("source", "created_at", "confirmed_at")
    actions = ["export_csv"]

    def export_csv(self, request, queryset):
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="subscribers.csv"'
        w = csv.writer(resp)
        w.writerow(["email","name","source","created_at","confirmed_at"])
        for s in queryset:
            w.writerow([s.email, s.name, s.source, s.created_at, s.confirmed_at])
        return resp
    export_csv.short_description = "Export selected to CSV"

class ArtistPhotoInline(admin.TabularInline):
    model = ArtistPhoto
    extra = 0

class ArtistVideoInline(admin.TabularInline):
    model = ArtistVideo
    extra = 0

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ("name","short_tag","is_public","sort","user")
    list_filter = ("is_public",)
    search_fields = ("name","short_tag")
    inlines = [ArtistPhotoInline, ArtistVideoInline]

class MediaItemInline(admin.TabularInline):
    model = MediaItem
    extra = 0

@admin.register(MediaAlbum)
class MediaAlbumAdmin(admin.ModelAdmin):
    list_display = ("title","date","city","state","is_public")
    list_filter = ("is_public","date","state")
    search_fields = ("title","city","state")
    inlines = [MediaItemInline]

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("name","slug","is_milestone","milestone_threshold","points")
    list_filter  = ("is_milestone",)
    search_fields= ("name","slug")

@admin.register(ShowBadge)
class ShowBadgeAdmin(admin.ModelAdmin):
    list_display = ("badge","show","code","active","starts_at","ends_at")
    list_filter  = ("active",)
    search_fields= ("code","show__venue_name","show__city","badge__name")

@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ("user","badge","show","source","acquired_at")
    list_filter  = ("source","badge")
    search_fields= ("user__username","badge__name","show__venue_name")

