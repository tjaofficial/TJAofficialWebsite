from django.urls import path, include
from . import views

app_name = "shop"

urlpatterns = [
    path("orders", views.orders_list, name="orders_list"),
    path("orders/<str:number>", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/ship/", views.mark_order_shipped, name="order_ship"),

    # Inventory
    path("products/inventory/", views.inventory_report, name="inventory"),

    # Products
    path("products/add/", views.product_add, name="product_add"),

    # Coupons
    path("coupons/", views.coupons_list, name="coupons"),
    path("coupons/new/", views.coupon_new, name="coupon_new"),
    path("coupons/<int:pk>/edit/", views.coupon_edit, name="coupon_edit"),
    path("coupons/issue-token/", views.issue_token, name="issue_token"),

    # Budget
    path("budget/", views.budget_sales, name="budget"),
    path("budget/export.csv", views.budget_export_csv, name="budget_export"),
]