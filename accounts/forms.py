from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django import forms
from .models import NfcHunt

User = get_user_model()

class InvitePasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        # Include active users even if they have an unusable password.
        return User._default_manager.filter(
            email__iexact=email,
            is_active=True,
        )

class NfcHuntForm(forms.ModelForm):
    class Meta:
        model = NfcHunt
        fields = [
            "event_name",
            "slug",
            "is_active",
            "required_locations",
            "locations_json",
            "start_at",
            "end_at",
            "completion_message",
            "reward_label",
        ]
        widgets = {
            "start_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "completion_message": forms.Textarea(attrs={"rows": 4}),
            "locations_json": forms.Textarea(attrs={"rows": 10}),
        }

    def clean_locations_json(self):
        value = self.cleaned_data.get("locations_json") or []
        if not isinstance(value, list):
            raise forms.ValidationError("Locations JSON must be a list.")
        return value