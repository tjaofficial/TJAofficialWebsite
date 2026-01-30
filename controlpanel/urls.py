from django.urls import path, include
from . import views

app_name = "control"

urlpatterns = [
    path("", views.dashboard, name="home"),
    path("artists/add/", views.control_add_artist, name="artist_add"),
    path("shop/", include(("shop.urls", "shop"), namespace="shop")),
    path("subs/", include(("subscribers.urls", "subscribers"), namespace="subscribers")),
    path("events/", include(("events.urls", "events"), namespace="events")),
    path("tickets/", include(("tickets.urls", "tickets"), namespace="tickets")),
    path("equipment/", include(("equipment.urls", 'equipment'), namespace="equipment")),
    path("pages/", include(("pages.cp_urls", "pages"), namespace="pages")),
    path("booking/", include("bookingstack.urls", namespace="bookingstack")),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("rewards/", include("rewards.urls_control", namespace="rewards_control")),
    path("setbuilder/", include(("setbuilder.urls_control", "setbuilder"), namespace="setbuilder")),
    path("media/submissions/", views.media_submissions_list, name="media_submissions_list"),
    path("media/submissions/<int:pk>/", views.media_submission_review, name="media_submission_review"),
    path("media/submissions/backfill-albums/", views.backfill_media_albums, name="media_backfill_albums"),
    path("media/albums/", views.media_albums_list, name="media_albums_list"),
    path("media/albums/<int:pk>/", views.media_album_edit, name="media_album_edit"),
    path("media/albums/<int:pk>/toggle-public/", views.media_album_toggle_public, name="media_album_toggle_public"),
    path("media/albums/<int:album_id>/items/<int:item_id>/edit/", views.media_item_edit, name="media_item_edit"
    ),
    path("media/albums/<int:album_id>/items/add/", views.media_item_add, name="media_item_add"),
    path("media/albums/<int:album_id>/items/<int:item_id>/delete/", views.media_item_delete, name="media_item_delete"),
    # path("music/", include("musiclib.urls")),
]