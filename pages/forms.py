from django import forms
from .models import Show, Subscriber, Artist, ArtistVideo
import time
from django.forms import inlineformset_factory


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

class ArtistCPForm(forms.ModelForm):
    class Meta:
        model = Artist
        fields = [
            "name","short_tag","genre","hometown","bio","avatar","hero_image",
            "is_public","sort",
            "website_url","instagram_url","tiktok_url",
            "youtube_url","spotify_url","apple_url","contact_email","default_role",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class":"input", "placeholder":"Name", "required": True}),
            "short_tag": forms.TextInput(attrs={"class":"input", "placeholder":"Short tag"}),
            "genre": forms.TextInput(attrs={"class":"input", "placeholder":"Genre"}),
            "hometown": forms.TextInput(attrs={"class":"input", "placeholder":"Hometown"}),
            "bio": forms.Textarea(attrs={"class":"input", "rows":3, "placeholder":"Bio"}),
            "avatar": forms.ClearableFileInput(attrs={"class":"input"}),
            "hero_image": forms.ClearableFileInput(attrs={"class":"input"}),
            "is_public": forms.CheckboxInput(),
            "sort": forms.NumberInput(attrs={"class":"input", "min":0}),
            "website_url": forms.URLInput(attrs={"class":"input", "placeholder":"https://"}),
            "instagram_url": forms.URLInput(attrs={"class":"input", "placeholder":"https://instagram.com/..."}),
            "tiktok_url": forms.URLInput(attrs={"class":"input", "placeholder":"https://tiktok.com/@..."}),
            "youtube_url": forms.URLInput(attrs={"class":"input", "placeholder":"https://youtube.com/@..."}),
            "spotify_url": forms.URLInput(attrs={"class":"input", "placeholder":"https://open.spotify.com/..."}),
            "apple_url": forms.URLInput(attrs={"class":"input", "placeholder":"https://music.apple.com/..."}),
            "contact_email": forms.EmailInput(attrs={"class":"input", "placeholder":"artist@email.com"}),
            "default_role": forms.Select(attrs={"class":"input"})
        }


class ArtistVideoForm(forms.ModelForm):
    class Meta:
        model = ArtistVideo
        fields = ["title", "url", "sort"]
        widgets = {
            "title": forms.TextInput(attrs={"class":"input", "placeholder":"Optional title"}),
            "url": forms.URLInput(attrs={"class":"input", "placeholder":"YouTube or Vimeo URL"}),
            "sort": forms.NumberInput(attrs={"class":"input", "min":0}),
        }

    def clean_url(self):
        u = self.cleaned_data.get("url","").strip()
        if not u:
            return u
        # light validation to ensure yt/vimeo-like
        import re
        if not (re.search(r"[?&]v=([A-Za-z0-9_-]{6,})", u) or
                re.search(r"youtu\.be/([A-Za-z0-9_-]{6,})", u) or
                re.search(r"vimeo\.com/(?:video/)?(\d+)", u)):
            raise forms.ValidationError("Must be a valid YouTube or Vimeo link.")
        return u

VideosFormSet = inlineformset_factory(
    Artist,
    ArtistVideo,
    form=ArtistVideoForm,
    fields=["title","url","sort"],
    extra=0,
    can_delete=True,
    validate_min=False,
    validate_max=False
)

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




