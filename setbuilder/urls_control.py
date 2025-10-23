# setbuilder/urls_control.py
from django.urls import path
from . import views_control as views

app_name = "setbuilder"

urlpatterns = [
    path("songs/", views.my_songs, name="songs"),
    path("songs/new/", views.song_new, name="song_new"),
    path("songs/<int:pk>/edit/", views.song_edit, name="song_edit"),
    path("songs/<int:pk>/delete/", views.song_delete, name="song_delete"),

    path("shows/", views.shows_list, name="shows_list"),
    path("shows/new/", views.build_show, name="build_show"),
    path("shows/<slug:slug>/edit/", views.build_show, name="show_edit"),
    path("shows/save/", views.save_show, name="save_show"),

    # Small JSON helpers for the modal
    path("api/songs/by-artist/<int:artist_id>/", views.api_songs_by_artist, name="api_songs_by_artist"),
]
