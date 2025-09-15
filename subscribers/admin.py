from django.contrib import admin
from .models import *
from django.http import HttpResponse
import csv

# Register your models here.
# @admin.register(Subscriber)
# class SubscriberAdmin(admin.ModelAdmin):
#     list_display = ("email", "name", "source", "created_at", "confirmed_at")
#     search_fields = ("email", "name", "source")
#     list_filter = ("source", "created_at", "confirmed_at")
#     actions = ["export_csv"]

#     def export_csv(self, request, queryset):
#         resp = HttpResponse(content_type="text/csv")
#         resp["Content-Disposition"] = 'attachment; filename="subscribers.csv"'
#         w = csv.writer(resp)
#         w.writerow(["email","name","source","created_at","confirmed_at"])
#         for s in queryset:
#             w.writerow([s.email, s.name, s.source, s.created_at, s.confirmed_at])
#         return resp
#     export_csv.short_description = "Export selected to CSV"