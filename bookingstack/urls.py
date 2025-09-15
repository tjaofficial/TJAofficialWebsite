from django.urls import path
from . import views

app_name = "bookingstack"
urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("venues/", views.venue_list, name="venue_list"),
    path("venues/<int:venue_id>/", views.venue_detail, name="venue_detail"),
    path("venues/<int:venue_id>/openers/", views.venue_openers, name="venue_openers"),
    path("compose/<int:venue_id>/", views.compose_pitch, name="compose_pitch"),
    path("epk/<int:venue_id>/", views.public_epk, name="public_epk"),
    path("fan/vote/<int:venue_id>/", views.fan_vote, name="fan_vote"),
    path("outreach/followups/", views.followup_queue, name="followup_queue"),
    path("inquiry/create/<int:venue_id>/", views.create_inquiry, name="create_inquiry"),
    path("compose/<int:venue_id>/refine/", views.refine_pitch, name="refine_pitch"),
    path("venues/<int:venue_id>/contact/add/", views.add_contact, name="add_contact"),
    path("outreach/<int:pk>/mark_reply/", views.mark_reply_received, name="mark_reply_received"),
    path("venues/<int:venue_id>/followup/bump/", views.bump_followup, name="bump_followup"),

    # Ops (buttons on the venue list)
    path("ops/refresh-metrics/", views.ops_refresh_metrics, name="ops_refresh_metrics"),
    path("ops/scrape-lineups/", views.ops_scrape_lineups, name="ops_scrape_lineups"),
    path("ops/remind-followups/", views.ops_remind_followups, name="ops_remind_followups"),
    path("ops/backfill-profiles/", views.ops_backfill_profiles, name="ops_backfill_profiles"),
]
