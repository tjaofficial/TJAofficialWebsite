from django.contrib import admin
from .models import *

@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ("event","name","price_cents","quantity","active","sales_start","sales_end")
    list_filter = ("active",)
    search_fields = ("event__name","name")
admin.site.register(Ticket)
admin.site.register(TicketReservation)