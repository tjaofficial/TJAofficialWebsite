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