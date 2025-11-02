from django.urls import path
from . import views

app_name = "tickets"

urlpatterns = [
    path("", views.tickettypes_list, name="list"),
    path("add/", views.tickettype_add, name="add"),
    path("<int:pk>/edit/", views.tickettype_edit, name="edit"),

     # QR + scan/check-in
    path("scan/", views.scan_page, name="scan"),
    path("scan/check/", views.scan_check, name="scan_check"),
    path("ticket/<uuid:token>/", views.public_ticket, name="ticket_detail"),
    path("admin-ticket/<uuid:token>/", views.admin_ticket, name="admin_ticket"),
    path("ticket/<uuid:token>/checkin/", views.ticket_checkin, name="ticket_checkin"),
    path("ticket/<uuid:token>/resend/", views.ticket_resend_email, name="ticket_resend"),
    path("qr/<uuid:token>.png", views.qr_png, name="qr_png"),

    # optional bulk issue for testing
    path("issue/", views.issue_tickets, name="issue"),

    path("webhook/stripe/", views.stripe_webhook, name="stripe_webhook"),

    path("scan/foh/", views.scan_foh, name="scan_foh"),
    path("api/scan/", views.scan_api, name="scan_api"),

    path("sales/", views.tickets_sold, name="sales"),
    path("sales/export.csv", views.tickets_sold_export, name="sales_export"),

    path("buy/<int:event_id>/", views.public_purchase, name="public_purchase"),
    path("buy/<int:event_id>/checkout/", views.public_create_checkout, name="public_checkout"),
    path("buy/<int:event_id>/success/", views.public_success, name="public_success"),
]
