# rewards/forms.py
from __future__ import annotations
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from tickets.models import TicketType
from shop.models import Product
from .models import RewardItem
from django.contrib.contenttypes.models import ContentType

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

class RewardItemForm(forms.ModelForm):
    fulfill_type = forms.ChoiceField(
        choices=RewardItem.FULFILL_CHOICES,
        widget=forms.Select(attrs={"class": "cp-select"})
    )
    # Conditional "target" helpers
    target_product = forms.ModelChoiceField(
        queryset=Product.objects.all().order_by("title"),
        required=False,
        widget=forms.Select(attrs={"class": "cp-select"})
    )
    target_ticket_type = forms.ModelChoiceField(
        queryset=TicketType.objects.select_related("event").order_by("-event__start","event__name","name"),
        required=False,
        widget=forms.Select(attrs={"class": "cp-select"})
    )

    class Meta:
        model = RewardItem
        fields = [
            "sku", "name", "description",
            "points_cost", "inventory", "is_active",
            "fulfill_type", "quantity_per_redeem",
        ]
        widgets = {
            "sku": forms.TextInput(attrs={"class":"cp-input"}),
            "name": forms.TextInput(attrs={"class":"cp-input"}),
            "description": forms.Textarea(attrs={"class":"cp-textarea","rows":3}),
            "points_cost": forms.NumberInput(attrs={"class":"cp-input","min":0}),
            "inventory": forms.NumberInput(attrs={"class":"cp-input","min":0}),
            "quantity_per_redeem": forms.NumberInput(attrs={"class":"cp-input","min":1}),
            "is_active": forms.CheckboxInput(attrs={"class":"cp-checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-fill target_* when editing
        if self.instance and self.instance.pk and self.instance.target_ct_id and self.instance.target_id:
            model = self.instance.target_ct.model
            if model == "product":
                self.fields["target_product"].initial = Product.objects.filter(pk=self.instance.target_id).first()
            elif model == "tickettype":
                self.fields["target_ticket_type"].initial = TicketType.objects.filter(pk=self.instance.target_id).first()

    def clean(self):
        cleaned = super().clean()
        ftype = cleaned.get("fulfill_type")
        prod = cleaned.get("target_product")
        tt   = cleaned.get("target_ticket_type")

        # Require the correct target depending on type
        if ftype == "PRODUCT" and not prod:
            raise forms.ValidationError("Select a Product for a PRODUCT reward.")
        if ftype == "TICKET" and not tt:
            raise forms.ValidationError("Select a Ticket Type for a TICKET reward.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        ftype = self.cleaned_data.get("fulfill_type")
        prod = self.cleaned_data.get("target_product")
        tt   = self.cleaned_data.get("target_ticket_type")

        # Map to generic target
        if ftype == "PRODUCT":
            ct = ContentType.objects.get_for_model(Product)
            obj.target_ct = ct
            obj.target_id = prod.pk
        elif ftype == "TICKET":
            ct = ContentType.objects.get_for_model(TicketType)
            obj.target_ct = ct
            obj.target_id = tt.pk
        else:
            obj.target_ct = None
            obj.target_id = None

        if commit:
            obj.save()
        return obj

class GiftAdHocForm(forms.Form):
    REWARD_TYPES = (
        ("TICKET", "Ticket(s) for a specific show"),
        ("PRODUCT", "Merch product"),
        ("COUPON", "Coupon / Promo Code"),   # enable if you want
        ("CUSTOM", "Custom gift (note only)"),
    )
    user = forms.ModelChoiceField(
        queryset=User.objects.all().order_by("email"),
        widget=forms.Select(attrs={"class": "cp-select"})
    )
    reward_type = forms.ChoiceField(
        choices=REWARD_TYPES,
        widget=forms.Select(attrs={"class": "cp-select"})
    )
    # Targets (conditional)
    ticket_type = forms.ModelChoiceField(
        queryset=TicketType.objects.select_related("event").order_by("-event__start","event__name","name"),
        required=False,
        widget=forms.Select(attrs={"class": "cp-select"})
    )
    product = forms.ModelChoiceField(
        queryset=Product.objects.all().order_by("title"),
        required=False,
        widget=forms.Select(attrs={"class": "cp-select"})
    )
    quantity = forms.IntegerField(min_value=1, initial=1, widget=forms.NumberInput(attrs={"class": "cp-input"}))
    note = forms.CharField(required=False, widget=forms.TextInput(attrs={"class":"cp-input", "placeholder":"optional admin note"}))
    email_recipient = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={"class":"cp-checkbox"}))

    def clean(self):
        cleaned = super().clean()
        rt = cleaned.get("reward_type")
        tt = cleaned.get("ticket_type")
        prod = cleaned.get("product")
        if rt == "TICKET" and not tt:
            raise forms.ValidationError("Select a Ticket Type for a ticket gift.")
        if rt == "PRODUCT" and not prod:
            raise forms.ValidationError("Select a Product for a product gift.")
        return cleaned