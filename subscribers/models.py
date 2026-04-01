import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Tag(models.Model):
    slug = models.SlugField(unique=True)
    label = models.CharField(max_length=60)

    def __str__(self):
        return self.label

class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=60, blank=True)
    last_name = models.CharField(max_length=60, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    city = models.CharField(max_length=60, blank=True)
    state = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=60, blank=True)
    birthday = models.DateField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=80, blank=True, help_text="Where they signed up (e.g., /email-signup)")
    consent = models.BooleanField(default=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    # NEW
    is_subscribed = models.BooleanField(default=True)
    unsubscribe_token = models.UUIDField(null=True, blank=True, editable=False)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def unsubscribe(self):
        self.is_subscribed = False
        self.unsubscribed_at = timezone.now()
        self.save(update_fields=["is_subscribed", "unsubscribed_at"])

    def __str__(self):
        return self.email

class SubscriberNote(models.Model):
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE, related_name="notes")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class EmailCampaign(models.Model):
    AUDIENCE_CHOICES = [
        ("subscribers", "Subscribers"),
        ("ticket_buyers", "Ticket Buyers"),
        ("rewards_accounts", "Rewards Accounts"),
        ("all_audiences", "All Audiences Combined"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sending", "Sending"),
        ("sent", "Sent"),
        ("partial", "Partial"),
        ("failed", "Failed"),
    ]

    title = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()

    audience_type = models.CharField(max_length=30, choices=AUDIENCE_CHOICES)
    event_id_snapshot = models.PositiveIntegerField(null=True, blank=True)
    event_name_snapshot = models.CharField(max_length=255, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_campaigns_created",
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    total_recipients = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.subject

class EmailCampaignRecipient(models.Model):
    campaign = models.ForeignKey(
        EmailCampaign,
        on_delete=models.CASCADE,
        related_name="recipients"
    )
    subscriber = models.ForeignKey(
        Subscriber,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_recipients"
    )

    email = models.EmailField()
    first_name = models.CharField(max_length=60, blank=True)
    last_name = models.CharField(max_length=60, blank=True)

    was_selected = models.BooleanField(default=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return f"{self.email} -> {self.campaign.subject}"
    
class EmailTemplate(models.Model):
    title = models.CharField(max_length=255, unique=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_templates_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title