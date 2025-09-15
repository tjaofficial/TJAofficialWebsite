from django import forms
from .models import TicketType

class TicketTypeForm(forms.ModelForm):
    class Meta:
        model = TicketType
        fields = ["event","name","price_cents","quantity","sales_start","sales_end","active"]
