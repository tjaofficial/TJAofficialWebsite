from django.db import models
from events.models import Event

class Equipment(models.Model):
    CATEGORY_CHOICES = [
        ("audio", "Audio"),
        ("lighting", "Lighting"),
        ("stage", "Stage"),
        ("video", "Video"),
        ("other", "Other"),
    ]
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")
    serial = models.CharField(max_length=120, blank=True)
    qty_total = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.category})"

class EventEquipment(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="equipment_assignments")
    equipment = models.ForeignKey("equipment.Equipment", on_delete=models.PROTECT, related_name="event_reservations")
    qty = models.PositiveIntegerField(default=1)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = [("event","equipment")]

    def __str__(self):
        return f"{self.event} — {self.equipment} x{self.qty}"