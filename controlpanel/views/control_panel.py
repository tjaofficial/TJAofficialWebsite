from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect
import secrets
from accounts.forms import InvitePasswordResetForm
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from ..forms import CreateArtistWithUserForm
from pages.models import Artist

User = get_user_model()
is_super = user_passes_test(lambda u: u.is_superuser)

@is_super
def dashboard(request):
    ctx = {
        "orders_today": 0,
        "subs_total": 0,
        "events_upcoming": 0,
    }
    return render(request, "controlpanel/dashboard.html", ctx)

def control_add_artist(request):
    if request.method == "POST":
        form = CreateArtistWithUserForm(request.POST, request.FILES)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]

            # 1) Create user with no usable password
            user = User.objects.create_user(username=username, email=email)
            user.set_unusable_password()
            user.is_active = True
            user.save()

            # Ensure profile exists & force reset if you keep the middleware
            profile = getattr(user, "profile", None)
            if profile:
                profile.must_reset_password = True
                profile.save(update_fields=["must_reset_password"])

            # 2) Create the Artist and link to user
            artist = form.save(commit=False)
            artist.user = user
            artist.save()

            # 3) Fire the password reset email (standard Django flow)
            prf = InvitePasswordResetForm(data={"email": email})
            if prf.is_valid():
                # uses the templates wired in accounts/urls.py
                prf.save(
                    request=request,
                    use_https=request.is_secure(),
                    email_template_name="accounts/password_reset_email.txt",
                    subject_template_name="accounts/password_reset_subject.txt",
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                )
                messages.success(request, f"Artist '{artist.name}' created. A password reset link was emailed to {email}.")
            else:
                messages.warning(request, "Artist created, but password reset email could not be prepared.")

            return redirect("control:pages_cp:artist_list")  # adjust
    else:
        form = CreateArtistWithUserForm()
    return render(request, "controlpanel/add_artist.html", {"form": form})

