from django.urls import path
from . import views

app_name = "events"

urlpatterns = [
    path("<int:event_id>/dashboard/", views.event_dashboard, name="dashboard"),
    path("", views.events_list, name="list"),
    path("add/", views.event_add, name="add"),
    path("<int:pk>/edit/", views.event_edit, name="edit"),
    path("venues/", views.venues_list, name="venues"),
    path("venues/add/", views.venue_add, name="venue_add"),

    path("<int:pk>/tickets/", views.event_tickets, name="tickets"),
    path("<int:pk>/tickets/checkout/", views.create_checkout, name="create_checkout"),
    path("tickets/success/", views.purchase_success, name="purchase_success"),
    path("tickets/cancel/", views.purchase_cancel, name="purchase_cancel"),
    # Tech directory
    path("tech/", views.tech_list, name="tech_list"),
    path("tech/add/", views.tech_add, name="tech_add"),
    path("tech/<int:pk>/edit/", views.tech_edit, name="tech_edit"),

    # Assign tech to event
    path("<int:event_id>/tech/", views.event_tech_list, name="event_tech_list"),
    path("<int:event_id>/tech/assign/", views.event_tech_assign, name="event_tech_assign"),
    path("<int:event_id>/tech/<int:assign_id>/remove/", views.event_tech_remove, name="event_tech_remove"),

    # Event media
    path("<int:event_id>/media/", views.event_media_list, name="event_media"),
    path("<int:event_id>/media/add/", views.event_media_add, name="event_media_add"),
    path("<int:event_id>/media/<int:media_id>/delete/", views.event_media_delete, name="event_media_delete"),

    # Artists Stuff
    path("<int:event_id>/artists/", views.event_artists, name="event_artists"),
    path("<int:event_id>/artists/assign/", views.event_artist_assign, name="event_artist_assign"),
    path("<int:event_id>/artists/<int:slot_id>/remove/", views.event_artist_remove, name="event_artist_remove"),
    path("<int:event_id>/artists/<int:slot_id>/link/", views.event_artist_link, name="event_artist_link"),
    path("<int:event_id>/artists/<uuid:token>/qr.png", views.artist_link_qr, name="artist_link_qr"),
    path("<int:event_id>/artist/<int:artist_id>/cash/", views.artist_cash_sale, name="artist_cash_sale"),

    path("r/a/<uuid:token>/", views.artist_link_redirect, name="artist_link_redirect"), 

    path("events/<int:event_id>/checklist/", views.checklist_view, name="event_checklist"),
    path("events/<int:event_id>/checklist/edit/", views.checklist_edit, name="event_checklist_edit"),
    path("events/checklist/toggle/<int:item_id>/", views.checklist_toggle, name="event_checklist_toggle"),
    path("events/<int:event_id>/checklist/reorder/", views.checklist_reorder, name="event_checklist_reorder"),
    path("<int:pk>/ics/", views.event_ics, name="ics"),
    # optional details page if you don't have one yet:
    path("<int:pk>/", views.event_detail, name="detail"),
]
