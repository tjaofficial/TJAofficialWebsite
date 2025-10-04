from django.urls import path
from . import views

app_name = "rewards"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("redeem/<int:item_id>/", views.redeem, name="redeem"),
    path("merge/", views.merge_history, name="merge"),
    path("staff/", views.staff_snapshot, name="staff"),
    path("rewards/catalog/", views.catalog, name="catalog"),
    path("rewards/redeem/<int:item_id>/", views.redeem, name="redeem"),
    path("rewards/claim/", views.claim_code, name="claim_code"),
]