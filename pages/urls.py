from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from events.views import public_events, event_details

urlpatterns = [
    path('', views.home, name='home'),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="/tour/"), name="logout"),
    path('shop/', views.shop, name='shop'),
    path("shop/<slug:slug>/add/", views.add_to_cart, name="shop_add_to_cart"),
    path("shop/<slug:slug>/", views.product_detail, name="product_detail"),
    path("cart/count/", views.cart_count, name="cart_count"),
    path("cart/", views.cart, name="cart"),
    path("cart/update/", views.cart_update, name="cart_update"),       # POST {product_id, qty}
    path("cart/remove/", views.cart_remove, name="cart_remove"),       # POST {product_id}
    path("cart/clear/", views.cart_clear, name="cart_clear"),          # POST
    path("checkout/", views.checkout, name="checkout"),
    path("cart/quote/", views.cart_quote, name="cart_quote"),   # POST for totals calc
    path("checkout/start/", views.checkout_start, name="checkout_start"),  # Stripe stub
    path("checkout/success/", views.checkout_success, name="checkout_success"),
    path("checkout/cancel/", views.checkout_cancel, name="checkout_cancel"),
    path("webhooks/stripe/", views.stripe_webhook, name="stripe_webhook"),
    path('music/', views.music, name='music'),
    path('shows/', views.shows, name='shows'),
    path("shows/new/", views.add_show, name="add_show"),
    path('videos/', views.videos, name='videos'),
    path('email-signup/', views.email_signup, name='email_signup'),
    path('day-n-night/', views.tour, name='tour'),
    path("tour/", views.tour_home, name="tour_home"),
    path("tour/headliners/", views.tour_headliners, name="tour_headliners"),
    path("tour/headliners/me/", views.tour_epk_edit_self, name="tour_epk_edit_self"),
    path("tour/headliners/<slug:slug>/", views.tour_epk_detail, name="tour_epk_detail"),
    path("tour/media/", views.tour_media, name="tour_media"),
    path("tour/shows/", views.tour_shows, name="tour_shows"),
    path("tour/passport/", views.tour_passport, name="tour_passport"),
    path("tour/passport/redeem/", views.tour_passport_redeem, name="tour_passport_redeem"),
    path("tour/passport/rules/", views.tour_passport_rules, name="tour_passport_rules"),
    path('links/', views.links, name='links'),
    path("events/", public_events, name="public_events"),
    path("events/<int:event_id>/<slug:slug>/", event_details, name="detail_slug"),
    path("events/<int:event_id>/", event_details, name="detail"),
    path("ticket/<uuid:token>/", views.ticket_detail, name="ticket_detail"),
    path("subscribe/", views.tour_subscribe, name="tour_subscribe"),
    #control panel
    
]