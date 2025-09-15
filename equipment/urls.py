from django.urls import path, include
from . import views

app_name = "equipment"

urlpatterns = [
    path("", views.equipment_list, name="list"),
    path("add/", views.equipment_add, name="add"),
    path("<int:pk>/edit/", views.equipment_edit, name="edit"),
    path("<int:pk>/delete/", views.equipment_delete, name="delete"),
    path("<int:event_id>/equipment/", views.event_equipment_list, name="event_equipment"),
    path("<int:event_id>/equipment/add/", views.event_equipment_add, name="event_equipment_add"),
    path("<int:event_id>/equipment/<int:res_id>/remove/", views.event_equipment_remove, name="event_equipment_remove"),
]