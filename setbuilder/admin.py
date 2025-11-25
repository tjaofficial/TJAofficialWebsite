# setbuilder/admin.py
from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html

from .models import Song, ShowSet, ShowItem


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "primary_artist",
        "genre",
        "is_collab",
        "collab_kind",
        "duration_admin",
        "created_at",
    )
    list_filter = ("genre", "is_collab", "collab_kind", "primary_artist")
    search_fields = (
        "title",
        "primary_artist__name",
        "collab_other",
        "collaborator_artists__name",
        "feeling",
    )
    autocomplete_fields = ("primary_artist", "collaborator_artists")
    filter_horizontal = ("collaborator_artists",)
    ordering = ("primary_artist__name", "title")
    readonly_fields = ("created_at",)

    fieldsets = (
        (None, {
            "fields": ("primary_artist", "title", "genre", "feeling")
        }),
        ("Duration", {
            "fields": ("duration_seconds",),
        }),
        ("Collaboration", {
            "fields": (
                "is_collab",
                "collab_kind",
                "collaborator_artists",
                "collab_other",
            )
        }),
        ("Meta", {
            "fields": ("created_at",),
        }),
    )

    @admin.display(description="Duration")
    def duration_admin(self, obj):
        return obj.duration_label


class ShowItemInline(admin.TabularInline):
    model = ShowItem
    extra = 0
    fields = (
        "sort",
        "kind",
        "artist",
        "song",
        "display_name",
        "duration_seconds",
        "duration_admin",
    )
    readonly_fields = ("duration_admin",)
    autocomplete_fields = ("artist", "song")
    ordering = ("sort", "id")

    @admin.display(description="Duration")
    def duration_admin(self, obj):
        if obj.duration_seconds:
            m, s = divmod(obj.duration_seconds, 60)
            return f"{m}:{s:02d}"
        return "—"


@admin.register(ShowSet)
class ShowSetAdmin(admin.ModelAdmin):
    list_display = (
        "label",
        "vibe",
        "created_by",
        "items_count",
        "total_duration",
        "created_at",
    )
    list_filter = ("vibe", "created_by", "created_at")
    search_fields = ("label", "slug", "created_by__username")
    prepopulated_fields = {"slug": ("label",)}
    autocomplete_fields = ("created_by",)
    readonly_fields = ("created_at", "total_duration", "items_count")
    inlines = (ShowItemInline,)
    ordering = ("-created_at", "-id")

    @admin.display(description="# Items")
    def items_count(self, obj):
        return obj.items.count()

    @admin.display(description="Total Length")
    def total_duration(self, obj):
        total = obj.items.aggregate(s=Sum("duration_seconds"))["s"] or 0
        m, s = divmod(total, 60)
        return f"{m}:{s:02d}"


@admin.register(ShowItem)
class ShowItemAdmin(admin.ModelAdmin):
    list_display = (
        "show",
        "sort",
        "kind",
        "artist",
        "song",
        "display_name",
        "duration_admin",
    )
    list_filter = ("kind", "show", "artist")
    search_fields = (
        "show__label",
        "artist__name",
        "song__title",
        "display_name",
    )
    autocomplete_fields = ("show", "artist", "song")
    ordering = ("show", "sort", "id")

    fieldsets = (
        (None, {
            "fields": ("show", "sort", "kind")
        }),
        ("References", {
            "fields": ("artist", "song"),
        }),
        ("Display / Duration", {
            "fields": ("display_name", "duration_seconds"),
        }),
    )

    @admin.display(description="Duration")
    def duration_admin(self, obj):
        if obj.duration_seconds:
            m, s = divmod(obj.duration_seconds, 60)
            return f"{m}:{s:02d}"
        return "—"
