from django.db import models

# Create your models here.
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
    consent = models.BooleanField(default=True)  # keep it simple; toggle if you need explicit checkbox
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)  # for double opt-in later

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
    
class SubscriberNote(models.Model):
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE, related_name="notes")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)