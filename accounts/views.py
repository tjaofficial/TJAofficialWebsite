from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.shortcuts import redirect
from pages.models import Artist
from django.urls import reverse

class LoginViewCustom(auth_views.LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True  # optional

    def get_success_url(self):
        # 1) honor explicit ?next=
        next_url = self.get_redirect_url()
        if next_url:
            return next_url
        # 2) send artists to their dashboard
        artist = Artist.objects.filter(user=self.request.user).first()
        print(artist)
        if artist:
            print("fucking shit")
            return reverse("control:pages:artist_dashboard", kwargs={"artist_id": artist.id})
        # 3) fallback (home, or wherever you like)
        elif self.request.user.is_superuser:
            return reverse("control:events:venues")
        else:
            return reverse("tour_passport")

class LogoutViewCustom(auth_views.LogoutView):
    next_page = "/"

class PasswordChangeViewCustom(auth_views.PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("control:accounts:password_change_done")

    def form_valid(self, form):
        resp = super().form_valid(form)
        # Unset the flag so user can navigate normally after changing pw
        profile = getattr(self.request.user, "profile", None)
        if profile and profile.must_reset_password:
            profile.must_reset_password = False
            profile.save(update_fields=["must_reset_password"])
        return resp

class PasswordChangeDoneViewCustom(auth_views.PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"

def redirect_login(request):
    if request.user.is_superuser:
        return redirect('control:events:venues')