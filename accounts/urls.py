from django.urls import path, re_path
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.LoginViewCustom.as_view(), name="login"),
    path("logout/", views.LogoutViewCustom.as_view(), name="logout"),
    path("password/change/", views.PasswordChangeViewCustom.as_view(), name="password_change"),
    path("password/change/done/", views.PasswordChangeDoneViewCustom.as_view(), name="password_change_done"),

    # RESET FLOW (email link)
    path("password/reset/", auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset.html",
        email_template_name="accounts/password_reset_email.txt",
        subject_template_name="accounts/password_reset_subject.txt",
        success_url="/control/accounts/password/reset/done/"
    ), name="password_reset"),
    path("password/reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html"
    ), name="password_reset_done"),
    re_path(r"^password/reset/confirm/(?P<uidb64>[-\w]+)/(?P<token>[-\w]+)/$", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html",
        success_url="/control/accounts/password/reset/complete/"
    ), name="password_reset_confirm"),
    path("password/reset/complete/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html"
    ), name="password_reset_complete"),
]
