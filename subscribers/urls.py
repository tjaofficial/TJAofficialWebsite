from django.urls import path
from . import views

app_name = "subscribers"

urlpatterns = [
    path("", views.subscribers_list, name="list"),
    path("add/", views.subscriber_add, name="add"),
    path("<int:pk>/", views.subscriber_detail, name="detail"),
    path("audience-outreach/", views.audience_outreach, name="audience_outreach"),
    path("unsubscribe/<uuid:token>/", views.unsubscribe, name="unsubscribe"),
    path("sync-ticket-buyers/", views.sync_ticket_buyers, name="sync_ticket_buyers"),
]
