from django import forms
from .models import Subscriber, Tag

class SubscriberForm(forms.ModelForm):
    class Meta:
        model = Subscriber
        fields = ["email", "first_name", "last_name", "phone",
                  "city", "state", "country", "birthday", "tags"]

class BulkSendForm(forms.Form):
    state = forms.CharField(required=False)
    birthday_month = forms.IntegerField(min_value=1, max_value=12, required=False)
    tags = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(), required=False)
    subject = forms.CharField(max_length=200)
    body = forms.CharField(widget=forms.Textarea)

class CampaignComposeForm(forms.Form):
    AUDIENCE_CHOICES = [
        ("event", "Specific Event Buyers"),
        ("all", "All Subscribers"),
    ]

    audience_type = forms.ChoiceField(
        choices=AUDIENCE_CHOICES,
        initial="event",
        widget=forms.Select(attrs={"class": "form-control"})
    )

    event_id = forms.IntegerField(required=False, widget=forms.HiddenInput())

    title = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Optional internal campaign title"
        })
    )

    subject = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Email subject"
        })
    )

    body = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 12,
            "placeholder": "Write your message here..."
        })
    )