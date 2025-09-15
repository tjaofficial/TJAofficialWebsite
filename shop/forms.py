from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import Product, ProductImage, Coupon, CouponToken
from subscribers.models import Subscriber

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "title", "slug", "description", "price_cents", "image", "image_url",
            "category", "is_active", "inventory", "sku", "has_variants"
        ]

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "alt", "sort"]

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = [
            "code", "percent_off", "amount_off_cents",
            "starts_at", "ends_at", "use_type", "max_uses", "token_ttl_days", "active"
        ]

class TokenIssueForm(forms.Form):
    coupon = forms.ModelChoiceField(queryset=Coupon.objects.all())
    subscriber = forms.ModelChoiceField(queryset=Subscriber.objects.all(), required=False)
    expire_in_days = forms.IntegerField(required=False, min_value=1)

    def save(self):
        coupon = self.cleaned_data["coupon"]
        subscriber = self.cleaned_data.get("subscriber")
        days = self.cleaned_data.get("expire_in_days")
        expires_at = timezone.now() + timedelta(days=days) if days else None
        return CouponToken.objects.create(
            coupon=coupon, subscriber=subscriber, expires_at=expires_at
        )
