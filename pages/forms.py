from django import forms
from .models import Show, Subscriber, Artist, ArtistVideo
import time

class ShowForm(forms.ModelForm):
    class Meta:
        model = Show
        fields = ["date", "venue_name", "city", "state", "tickets_url"]

        widgets = {
            # Native browser date+time control; format below matches this widget
            "date": forms.DateTimeInput(
                attrs={"type": "datetime-local", "placeholder": "YYYY-MM-DD HH:MM"},
                format="%Y-%m-%dT%H:%M",
            ),
            "venue_name": forms.TextInput(attrs={"placeholder": "Venue name"}),
            "city": forms.TextInput(attrs={"placeholder": "City"}),
            "state": forms.TextInput(attrs={"placeholder": "State (e.g., MI)"}),
            "tickets_url": forms.URLInput(attrs={"placeholder": "https://tickets.example.com/..."}),
        }

    # Make sure the form accepts the HTML5 datetime-local format
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"]

class EmailSignupForm(forms.ModelForm):
    # Honeypot field (hidden in CSS). Real users leave empty.
    website = forms.CharField(required=False)  # bots often fill this
    # Timestamp to deter instant bot posts
    ts = forms.IntegerField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Subscriber
        fields = ["email", "name"]
        widgets = {
            "email": forms.EmailInput(attrs={"placeholder":"you@example.com", "autocomplete":"email"}),
            "name": forms.TextInput(attrs={"placeholder":"Your name (optional)", "autocomplete":"name"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("website"):
            raise forms.ValidationError("Bot detected.")
        # basic time check: at least ~2s since page render
        try:
            ts = int(cleaned.get("ts") or 0)
            if time.time() - ts < 2:
                raise forms.ValidationError("Please try again.")
        except Exception:
            pass
        return cleaned

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class ArtistEPKForm(forms.ModelForm):
    class Meta:
        model = Artist
        fields = [
            "name","short_tag","genre","hometown","bio",
            "avatar","hero_image",
            "website_url","instagram_url","tiktok_url","youtube_url","spotify_url","apple_url",
            "contact_email",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 6, "placeholder": "Artist bio..."}),
        }

class ArtistVideoForm(forms.ModelForm):
    class Meta:
        model = ArtistVideo
        fields = ["url", "title", "sort"]

class ArtistPhotoUploadForm(forms.Form):
    new_photos = forms.ImageField(
        required=False,
        widget=MultipleFileInput(attrs={"multiple": True, "accept": "image/*"})
    )
    def clean_new_photos(self):
        files = self.files.getlist("new_photos")
        for f in files:
            if f.size > 8 * 1024 * 1024:
                raise forms.ValidationError("Each image must be under 8MB.")
        return files




