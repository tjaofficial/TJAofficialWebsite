from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import NfcHunt, NfcHuntEntry


@admin.register(NfcHunt)
class NfcHuntAdmin(admin.ModelAdmin):
    list_display = (
        "event_name",
        "slug",
        "is_active",
        "required_locations",
        "start_at",
        "end_at",
        "created_at",
    )
    search_fields = ("event_name", "slug")
    list_filter = ("is_active", "created_at", "start_at", "end_at")
    prepopulated_fields = {"slug": ("event_name",)}


@admin.register(NfcHuntEntry)
class NfcHuntEntryAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "hunt",
        "completed",
        "redeemed",
        "completed_at",
        "redeemed_at",
        "created_at",
    )
    search_fields = (
        "user__username",
        "user__email",
        "hunt__event_name",
        "hunt__slug",
        "qr_token",
    )
    list_filter = (
        "completed",
        "redeemed",
        "created_at",
        "completed_at",
        "redeemed_at",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "completed_at",
        "qr_generated_at",
        "redeemed_at",
    )