from django.contrib import admin
from .models import *

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name","city","state","capacity")
    search_fields = ("name","city","state")

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name","start","venue","published","is_tour_stop")
    list_filter = ("published","is_tour_stop")
    search_fields = ("name",)

@admin.register(TechPerson)
class TechPersonAdmin(admin.ModelAdmin):
    list_display = ("name","role","city","state","active","rate_cents")
    list_filter = ("role","active","state")
    search_fields = ("name","email","phone","city","state")

@admin.register(EventTechAssignment)
class EventTechAssignmentAdmin(admin.ModelAdmin):
    list_display = ("event","person","role","confirmed","rate_cents")
    list_filter = ("confirmed","role")
    search_fields = ("event__name","person__name")

@admin.register(EventMedia)
class EventMediaAdmin(admin.ModelAdmin):
    list_display = ("event","kind","caption","uploaded_at")
    list_filter = ("kind",)
    search_fields = ("event__name","caption")

from django.contrib import admin
from .models import ChecklistTemplate, ChecklistTemplateItem, EventChecklist, EventChecklistItem

class ChecklistTemplateItemInline(admin.TabularInline):
    model = ChecklistTemplateItem
    extra = 0

@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    inlines = [ChecklistTemplateItemInline]

class EventChecklistItemInline(admin.TabularInline):
    model = EventChecklistItem
    extra = 0

@admin.register(EventChecklist)
class EventChecklistAdmin(admin.ModelAdmin):
    inlines = [EventChecklistItemInline]

admin.site.register(EventArtist)
admin.site.register(ArtistSaleLink)