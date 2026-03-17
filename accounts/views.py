from django.contrib.auth import views as auth_views
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy, reverse
from pages.models import Artist
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.contrib.admin.views.decorators import staff_member_required
from .models import NfcHunt, NfcHuntEntry
from .forms import NfcHuntForm

is_super = user_passes_test(lambda u: u.is_superuser)

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
            return reverse("rewards:dashboard")

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
    
@login_required
@require_GET
def hunt_tap_view(request, hunt_slug, location_key):
    hunt = get_object_or_404(NfcHunt, slug=hunt_slug)

    if not hunt.is_currently_active():
        messages.error(request, "This hunt is not active right now.")
        return redirect("control:accounts:hunt_progress", hunt_slug=hunt.slug)

    location_config = hunt.get_location_config(location_key)
    if not location_config:
        raise Http404("Invalid hunt location.")

    entry, created = NfcHuntEntry.objects.get_or_create(
        user=request.user,
        hunt=hunt,
    )

    entry.initialize_progress(save=False)
    already_found = entry.progress_json.get(location_key, {}).get("found", False)

    if not already_found:
        entry.mark_location_found(location_key, save=True)
        messages.success(request, f"You found: {location_config.get('label', location_key)}")
    else:
        messages.info(request, f"You already found: {location_config.get('label', location_key)}")

    if entry.completed:
        return redirect("control:accounts:hunt_complete", hunt_slug=hunt.slug)

    return redirect("control:accounts:hunt_progress", hunt_slug=hunt.slug)

@login_required
@require_GET
def hunt_progress_view(request, hunt_slug):
    hunt = get_object_or_404(NfcHunt, slug=hunt_slug)

    entry, created = NfcHuntEntry.objects.get_or_create(
        user=request.user,
        hunt=hunt,
    )
    entry.initialize_progress(save=True)

    location_rows = []
    for location in hunt.locations_json or []:
        key = location.get("key")
        progress_data = entry.progress_json.get(key, {})
        location_rows.append({
            "key": key,
            "label": location.get("label", key),
            "path": location.get("path", key),
            "found": progress_data.get("found", False),
            "found_at": progress_data.get("found_at"),
        })

    context = {
        "hunt": hunt,
        "entry": entry,
        "location_rows": location_rows,
        "found_count": entry.get_found_count(),
        "required_count": hunt.get_required_count(),
        "progress_percent": entry.get_progress_percent(),
    }
    return render(request, "accounts/hunt/progress.html", context)

@login_required
@require_GET
def hunt_complete_view(request, hunt_slug):
    hunt = get_object_or_404(NfcHunt, slug=hunt_slug)
    entry = get_object_or_404(NfcHuntEntry, user=request.user, hunt=hunt)

    entry.initialize_progress(save=False)
    entry.update_completion(save=True)

    if not entry.completed:
        messages.warning(request, "You have not completed all hunt locations yet.")
        return redirect("control:accounts:hunt_progress", hunt_slug=hunt.slug)

    context = {
        "hunt": hunt,
        "entry": entry,
        "qr_token": entry.qr_token,
    }
    return render(request, "accounts/hunt/completed.html", context)

@staff_member_required
@require_POST
def hunt_redeem_view(request, qr_token):
    entry = get_object_or_404(NfcHuntEntry, qr_token=qr_token)

    if not entry.completed:
        return JsonResponse({
            "success": False,
            "message": "This hunt entry is not completed."
        }, status=400)

    if entry.redeemed:
        return JsonResponse({
            "success": False,
            "message": "This reward has already been redeemed.",
            "redeemed_at": entry.redeemed_at.isoformat() if entry.redeemed_at else None,
        }, status=400)

    entry.redeemed = True
    entry.redeemed_at = timezone.now()
    entry.save(update_fields=["redeemed", "redeemed_at", "updated_at"])

    return JsonResponse({
        "success": True,
        "message": "Reward redeemed successfully.",
        "user": str(entry.user),
        "hunt": entry.hunt.event_name,
        "redeemed_at": entry.redeemed_at.isoformat(),
    })

@is_super
def hunt_admin_list_view(request):
    hunts = NfcHunt.objects.all().order_by("-updated_at", "-created_at")
    return render(request, "accounts/hunt/admin_list.html", {
        "hunts": hunts,
    })

@is_super
def hunt_admin_add_view(request):
    form = NfcHuntForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        hunt = form.save()
        return redirect("control:accounts:nfc_hunt_admin_edit", pk=hunt.pk)

    return render(request, "accounts/hunt/admin_form.html", {
        "form": form,
        "hunt": None,
    })

@is_super
def hunt_admin_edit_view(request, pk):
    hunt = get_object_or_404(NfcHunt, pk=pk)
    form = NfcHuntForm(request.POST or None, instance=hunt)

    if request.method == "POST" and form.is_valid():
        hunt = form.save()
        return redirect("control:accounts:nfc_hunt_admin_edit", pk=hunt.pk)

    return render(request, "accounts/hunt/admin_form.html", {
        "form": form,
        "hunt": hunt,
    })


