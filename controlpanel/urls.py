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
    # path("music/", include("musiclib.urls")),
]