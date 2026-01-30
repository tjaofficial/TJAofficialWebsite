from django.contrib import admin
from .models import *

# Register your models here.

admin.site.register(Show)


class TrackInline(admin.TabularInline):
    model = Track
    extra = 0

@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = ("title", "release_type", "release_date")
    list_filter = ("release_type", "release_date")
    search_fields = ("title",)
    inlines = [TrackInline]

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "published_at", "is_public", "sort")
    list_filter = ("is_public",)
    search_fields = ("title", "youtube_url")

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


admin.site.register(Subscriber)


@admin.register(MediaSubmission)
class MediaSubmissionAdmin(admin.ModelAdmin):
    list_display = ("album", "status", "name", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "email", "caption", "album__title", "album__city", "album__state")
    actions = ("approve_selected", "decline_selected")

    def approve_selected(self, request, queryset):
        for sub in queryset.filter(status="pending"):
            item = MediaItem(album=sub.album, caption=sub.caption or "", sort=0)
            if sub.image:
                item.kind = "photo"
                item.image = sub.image
            else:
                item.kind = "video"
                item.url = sub.video_url
            item.save()

            # optionally auto set album cover if none yet
            if sub.album.cover_item_id is None and item.kind == "photo" and item.image:
                sub.album.cover_item = item
                sub.album.save(update_fields=["cover_item"])

            sub.status = "approved"
            sub.save(update_fields=["status"])
    approve_selected.short_description = "Approve selected (creates MediaItems)"

    def decline_selected(self, request, queryset):
        queryset.delete()
    decline_selected.short_description = "Decline selected (delete)"