# rewards/forms.py
from __future__ import annotations
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import CustomerProfile

User = get_user_model()

SEX_CHOICES = (
    ("", "Select..."),
    ("M", "Male"),
    ("F", "Female")
)

class SignupForm(forms.Form):
    # Account
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    confirm_password = forms.CharField(label="Confirm Password", widget=forms.PasswordInput())
    username = forms.CharField(label="Username", max_length=30)
    first_name = forms.CharField(label="First Name", max_length=30, widget=forms.TextInput(attrs={"required": True}))
    last_name = forms.CharField(label="Last Name", max_length=30, widget=forms.TextInput(attrs={"required": True}))
    # Contact & Birthday
    phone = forms.CharField(label="Phone", max_length=32, required=False)
    birthday = forms.DateField(label="Birthday", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    sex = forms.ChoiceField(label="Sex", choices=SEX_CHOICES, required=False)

    # Shipping
    ship_name = forms.CharField(label="Full Name (Shipping)", max_length=255, required=False)
    ship_line1 = forms.CharField(label="Address Line 1", max_length=255, required=False)
    ship_line2 = forms.CharField(label="Address Line 2", max_length=255, required=False)
    ship_city = forms.CharField(label="City", max_length=100, required=False)
    ship_state = forms.CharField(label="State/Province", max_length=100, required=False)
    ship_postal = forms.CharField(label="Postal Code", max_length=20, required=False)
    ship_country = forms.CharField(label="Country", max_length=2, required=False, initial="US")

    # Marketing + Terms
    marketing_opt_in = forms.BooleanField(label="Email me rewards news, drops & exclusive offers", required=False)
    accept_terms = forms.BooleanField(label="I agree to the Terms & Privacy", required=True)

    # Tiny honeypot (basic bot deter)
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1", "style": "position:absolute;left:-9999px;"}))

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists. Try logging in.")
        return email

    def clean(self):
        data = super().clean()
        if data.get("password") != data.get("confirm_password"):
            self.add_error("confirm_password", "Passwords do not match.")
        if data.get("website"):  # honeypot filled
            raise ValidationError("Invalid submission.")
        return data

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if not username:
            raise ValidationError("Please choose a username.")
        if any(ch in username for ch in " @/:\\?#[]!$&'()*+,;=\"<>"):
            raise ValidationError("Username has invalid characters.")
        if get_user_model().objects.filter(username__iexact=username).exists():
            raise ValidationError("That username is taken.")
        return username
