from django.contrib import admin
from .models import *


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("label", "slug")
    search_fields = ("label", "slug")


class SubscriberNoteInline(admin.TabularInline):
    model = SubscriberNote
    extra = 0


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name", "city", "state", "consent", "is_subscribed", "source", "created_at")
    list_filter = ("consent", "is_subscribed", "source", "state", "country", "tags")
    search_fields = ("email", "first_name", "last_name", "city", "state")
    inlines = [SubscriberNoteInline]
    filter_horizontal = ("tags",)


class EmailCampaignRecipientInline(admin.TabularInline):
    model = EmailCampaignRecipient
    extra = 0
    readonly_fields = ("email", "first_name", "last_name", "sent_at", "failed_at", "error_message")


@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = ("subject", "audience_type", "status", "total_recipients", "sent_count", "failed_count", "created_at")
    list_filter = ("status", "audience_type", "created_at")
    search_fields = ("subject", "title", "event_name_snapshot")
    inlines = [EmailCampaignRecipientInline]


@admin.register(EmailCampaignRecipient)
class EmailCampaignRecipientAdmin(admin.ModelAdmin):
    list_display = ("email", "campaign", "sent_at", "failed_at")
    search_fields = ("email", "first_name", "last_name", "campaign__subject")

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "created_at", "updated_at")
    search_fields = ("title", "subject", "body")