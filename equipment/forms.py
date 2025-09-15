from django import forms
from .models import *
from django.core.exceptions import ValidationError

class EventEquipmentForm(forms.ModelForm):
    class Meta:
        model = EventEquipment
        fields = ["equipment", "qty"]

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop("event")
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        eq = cleaned.get("equipment")
        if eq and EventEquipment.objects.filter(event=self.event, equipment=eq).exists():
            raise ValidationError("That equipment is already assigned to this event.")
        return cleaned

class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ["name", "category", "serial", "qty_total", "notes", "active"]