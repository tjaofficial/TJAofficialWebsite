from django.urls import path
from . import views

app_name = "subscribers"

urlpatterns = [
    path("", views.subscribers_list, name="list"),
    path("add/", views.subscriber_add, name="add"),
    path("<int:pk>/", views.subscriber_detail, name="detail"),
    path("send/", views.bulk_send, name="send"),
]
