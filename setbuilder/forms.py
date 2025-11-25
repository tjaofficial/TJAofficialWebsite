from django.forms import ModelForm
from .models import Song
from django import forms

# ---------- Forms ----------
class SongForm(ModelForm):
    minutes = forms.IntegerField(min_value=0, required=False, label="Minutes")
    seconds = forms.IntegerField(min_value=0, max_value=59, required=False, label="Seconds")

    class Meta:
        model = Song
        fields = [
            "title",
            "is_collab",
            "collab_kind",
            "collaborator_artists",
            "collab_other",
            "genre",
            "feeling",
            "primary_artist"
        ]

    def clean(self):
        cleaned = super().clean()

        mins = cleaned.get("minutes") or 0
        secs = cleaned.get("seconds") or 0

        duration = mins * 60 + secs

        if duration <= 0:
            raise forms.ValidationError("Duration must be greater than zero.")

        cleaned["duration_seconds"] = duration
        return cleaned
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.duration_seconds = self.cleaned_data["duration_seconds"]
        if commit:
            instance.save()
            self.save_m2m()
        return instance