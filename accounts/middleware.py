from django.shortcuts import redirect
from django.urls import reverse

EXEMPT_NAMES = {
    "accounts:password_change",
    "accounts:password_change_done",
    "accounts:login",
    "accounts:logout",
}  # add other names you want to allow

class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        u = request.user
        if u.is_authenticated:
            # If user has no profile, create it (safety)
            profile = getattr(u, "profile", None)
            if profile and profile.must_reset_password:
                # allow only password-change flow, logout, and static/media/admin
                if not getattr(request, "resolver_match", None):
                    return self.get_response(request)
                name = request.resolver_match.view_name
                if name not in EXEMPT_NAMES and not name.startswith("admin:"):
                    return redirect(reverse("accounts:password_change"))
        return self.get_response(request)
