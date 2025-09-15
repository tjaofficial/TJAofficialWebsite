# bookingstack/admin.py
from django.contrib import admin
from .models import (
    VenueProfile, VenueContact, Outreach, ShowInquiry,
    TechAsset, EpkVisit, FanSupport, SocialMetricSnapshot
)

@admin.register(VenueProfile)
class VenueProfileAdmin(admin.ModelAdmin):
    list_display = ("venue", "booking_email", "booking_phone", "last_lineup_scrape")
    search_fields = ("venue__name", "booking_email", "booking_phone")
    # NOTE: No inlines here because VenueContact/Outreach FK to Venue, not VenueProfile.

@admin.register(VenueContact)
class VenueContactAdmin(admin.ModelAdmin):
    list_display = ("venue", "name", "role", "email", "phone", "is_primary")
    list_filter = ("is_primary", "role")
    search_fields = ("venue__name", "name", "email", "phone")

@admin.register(Outreach)
class OutreachAdmin(admin.ModelAdmin):
    list_display = ("venue", "kind", "subject", "sent_at", "reply_received", "next_followup_at")
    list_filter = ("kind", "reply_received")
    search_fields = ("venue__name", "subject", "body")
    autocomplete_fields = ("contact",)

@admin.register(ShowInquiry)
class ShowInquiryAdmin(admin.ModelAdmin):
    list_display = ("venue", "status", "hard_date", "target_start", "target_end", "expected_draw", "hold_expires")
    list_filter = ("status",)
    search_fields = ("venue__name", "notes")

@admin.register(TechAsset)
class TechAssetAdmin(admin.ModelAdmin):
    list_display = ("kind", "file", "created_at")
    list_filter = ("kind",)

@admin.register(EpkVisit)
class EpkVisitAdmin(admin.ModelAdmin):
    list_display = ("venue", "opened_at", "referrer", "ip")
    list_filter = ("opened_at",)
    search_fields = ("venue__name", "referrer", "ip", "user_agent")

@admin.register(FanSupport)
class FanSupportAdmin(admin.ModelAdmin):
    list_display = ("venue", "name", "email", "postal_code", "created_at")
    list_filter = ("created_at",)
    search_fields = ("venue__name", "name", "email", "postal_code")

@admin.register(SocialMetricSnapshot)
class SocialMetricSnapshotAdmin(admin.ModelAdmin):
    list_display = ("created_at", "city", "metro_radius_km",
                    "spotify_monthly_listeners", "instagram_local_followers", "tiktok_local_followers")
    list_filter = ("city",)
    search_fields = ("city",)

from .models import OpenerMap
@admin.register(OpenerMap)
class OpenerMapAdmin(admin.ModelAdmin):
    list_display = ("venue","artist_name","contact_url","last_seen")
    search_fields = ("venue__name","artist_name")
