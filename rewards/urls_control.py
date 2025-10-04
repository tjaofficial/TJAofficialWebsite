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
    path("rewards/", views.reward_items_list, name="items"),
    path("rewards/new/", views.reward_item_new, name="item_new"),
    path("rewards/<int:pk>/edit/", views.reward_item_edit, name="item_edit"),
    path("rewards/<int:pk>/delete/", views.reward_item_delete, name="item_delete"),
    path("rewards/gift/", views.gift_reward, name="gift"),
]
