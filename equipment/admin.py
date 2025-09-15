# equipment/admin.py
from django.contrib import admin
from .models import *

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("name","category","qty_total","active")
    list_filter = ("category","active")
    search_fields = ("name","serial")


admin.site.register(EventEquipment)