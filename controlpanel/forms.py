from django import forms
from django.contrib.auth import get_user_model
from pages.models import Artist  # adjust import path

User = get_user_model()

class CreateArtistWithUserForm(forms.ModelForm):
    username = forms.CharField()
    email = forms.EmailField()

    class Meta:
        model = Artist
        fields = ["name", "genre", "hometown"]  # add/adjust your Artist fields

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
