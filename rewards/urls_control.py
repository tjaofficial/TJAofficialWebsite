# rewards/urls_control.py
from django.urls import path
from . import control_views as views

app_name = "rewards_control"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("accounts/", views.accounts, name="accounts"),
    path("accounts/<int:user_id>/", views.account_detail, name="account_detail"),
    path("purchases/", views.purchases, name="purchases"),
    path("redemptions/", views.redemptions, name="redemptions"),
]
