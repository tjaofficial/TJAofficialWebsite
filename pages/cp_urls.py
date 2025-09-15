from django.urls import path
from . import cp_views

app_name = "pages_cp"

urlpatterns = [
    path("artists/", cp_views.artist_list, name="artist_list"),
    path("artists/add/", cp_views.artist_add, name="artist_add"),
    path("artists/<int:artist_id>/dashboard/", cp_views.artist_dashboard, name="artist_dashboard"),
    path("artists/<int:pk>/edit/", cp_views.artist_edit, name="artist_edit"),
]
