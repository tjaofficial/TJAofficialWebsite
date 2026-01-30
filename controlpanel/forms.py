from django import forms
from django.contrib.auth import get_user_model
from pages.models import Artist, MediaSubmission, MediaAlbum, MediaItem  # adjust import path
from django.forms.widgets import FileInput, ClearableFileInput

class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultiFileField(forms.FileField):
    """
    A FileField that accepts multiple uploaded files.
    Returns a list of UploadedFile objects.
    """
    widget = MultiFileInput

    def clean(self, data, initial=None):
        # data might be a single file or a list of files depending on widget
        if data in (None, "", []):
            return []

        if not isinstance(data, (list, tuple)):
            data = [data]

        cleaned_files = []
        for f in data:
            cleaned_files.append(super().clean(f, initial))
        return cleaned_files

User = get_user_model()

class CreateArtistWithUserForm(forms.ModelForm):
    username = forms.CharField()
    email = forms.EmailField()

    class Meta:
        model = Artist
        fields = ["name", "genre", "hometown", "default_role", "bio",
                  "avatar", "hero_image", "website_url", "instagram_url",
                  "tiktok_url", "youtube_url", "spotify_url", "apple_url",
                  "contact_email", "is_public"]

    def clean_username(self):
        u = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=u).exists():
            raise forms.ValidationError("Username already exists.")
        return u

    def clean_email(self):
        e = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=e).exists():
            # optional: allow duplicates, but usually you don’t want
            raise forms.ValidationError("Email already in use.")
        return e

class MediaSubmissionReviewForm(forms.ModelForm):
    class Meta:
        model = MediaSubmission
        fields = ["album", "name", "email", "image", "video_url", "caption"]
        widgets = {
            "caption": forms.TextInput(attrs={"maxlength": 220}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # show newest albums first (and include non-public albums if you want moderation to target them)
        self.fields["album"].queryset = MediaAlbum.objects.order_by("-date", "-id")

class MediaAlbumForm(forms.ModelForm):
    class Meta:
        model = MediaAlbum
        fields = ["title", "show", "city", "state", "date", "is_public", "sort", "cover_item"]

class MediaItemForm(forms.ModelForm):
    class Meta:
        model = MediaItem
        fields = ["kind", "image", "url", "caption", "sort"]

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")
        image = cleaned.get("image")
        url = (cleaned.get("url") or "").strip()

        # If editing, instance may already have an image
        has_existing_image = bool(getattr(self.instance, "pk", None) and getattr(self.instance, "image", None))

        if kind == "photo":
            # allow no new image if one already exists
            if not image and not has_existing_image:
                raise forms.ValidationError("Photo kind requires an image upload.")
            cleaned["url"] = ""

        elif kind == "video":
            if not url:
                raise forms.ValidationError("Video kind requires a URL.")
            # If switching from photo -> video, clear image
            cleaned["image"] = None

        return cleaned
    
class MediaItemAddForm(forms.Form):
    KIND_CHOICES = [("photo","Photo"), ("video","Video")]

    kind = forms.ChoiceField(choices=KIND_CHOICES, initial="photo")
    caption = forms.CharField(required=False, max_length=200)
    url = forms.URLField(required=False, help_text="YouTube/Vimeo link (videos only)")
    sort = forms.IntegerField(required=False, initial=0)

    images = MultiFileField(
        required=False,
        widget=MultiFileInput(attrs={"multiple": True}),
        help_text="Upload one or more photos"
    )

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")
        url = (cleaned.get("url") or "").strip()
        images = cleaned.get("images") or []   # ✅ now this is a LIST

        if kind == "photo":
            if not images:
                raise forms.ValidationError("Choose at least one image for Photo.")
            cleaned["url"] = ""

        elif kind == "video":
            if not url:
                raise forms.ValidationError("Paste a video URL for Video.")
            if images:
                raise forms.ValidationError("Videos can’t include uploaded images. Remove the files or switch to Photo.")

        return cleaned


