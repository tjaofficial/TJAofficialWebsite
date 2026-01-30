from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from accounts.forms import InvitePasswordResetForm
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.conf import settings
from ..forms import CreateArtistWithUserForm, MediaSubmissionReviewForm, MediaItemForm, MediaAlbumForm, MediaItemAddForm
from events.models import Event
from pages.models import MediaAlbum, MediaSubmission, MediaItem
from django.db import transaction
from django.utils.text import slugify
from django.db.models import Q, Count
from django.views.decorators.http import require_POST

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

@is_super
def media_submissions_list(request):
    status = (request.GET.get("status") or "pending").strip()

    qs = MediaSubmission.objects.select_related("album").order_by("-created_at")
    if status in ("pending", "approved", "declined"):
        qs = qs.filter(status=status)

    counts = {
        "pending": MediaSubmission.objects.filter(status="pending").count(),
        "approved": MediaSubmission.objects.filter(status="approved").count(),
        "declined": MediaSubmission.objects.filter(status="declined").count(),
    }

    return render(request, "controlpanel/media_submissions_list.html", {
        "subs": qs[:300],  # keep it sane
        "status": status,
        "counts": counts,
    })

@is_super
def media_submission_review(request, pk):
    sub = get_object_or_404(MediaSubmission.objects.select_related("album"), pk=pk)

    form = MediaSubmissionReviewForm(request.POST or None, request.FILES or None, instance=sub)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "save":
            if form.is_valid():
                form.save()
                messages.success(request, "Saved changes.")
                return redirect("control:media_submission_review", pk=sub.id)

        elif action == "approve":
            if sub.status == "approved":
                messages.info(request, "Already approved.")
                return redirect("control:media_submission_review", pk=sub.id)

            if not form.is_valid():
                messages.error(request, "Fix the errors before approving.")
            else:
                with transaction.atomic():
                    sub = form.save()  # save edits first

                    # Create MediaItem in the album
                    if sub.image:
                        MediaItem.objects.create(
                            album=sub.album,
                            kind="photo",
                            image=sub.image,
                            caption=sub.caption or "",
                        )
                    else:
                        MediaItem.objects.create(
                            album=sub.album,
                            kind="video",
                            url=sub.video_url,
                            caption=sub.caption or "",
                        )

                    sub.status = "approved"
                    sub.save(update_fields=["status"])

                messages.success(request, "Approved — added to album.")
                return redirect("control:media_submissions_list")

        elif action == "deny":
            # delete the file too (important if image)
            if sub.image:
                sub.image.delete(save=False)
            sub.delete()
            messages.warning(request, "Denied — submission deleted.")
            return redirect("control:media_submissions_list")

    return render(request, "controlpanel/media_submission_review.html", {
        "sub": sub,
        "form": form,
    })

@is_super
@transaction.atomic
def backfill_media_albums(request):
    if request.method != "POST":
        messages.error(request, "POST required.")
        return redirect("control:media_submissions_list")

    # Events with ZERO albums
    # (because MediaAlbum.show FK has related_name="media_album")
    missing = (Event.objects
               .filter(media_album__isnull=True)
               .select_related("venue")
               .order_by("start"))

    created = 0
    for ev in missing:
        city  = (ev.venue.city if ev.venue else "") or ""
        state = (ev.venue.state if ev.venue else "") or ""
        date  = ev.start.date() if ev.start else None

        pretty_date = date.strftime("%b %d, %Y") if date else "Undated"
        title = f"{city}, {state} — {pretty_date}".strip(" ,—") or (ev.name or f"Event {ev.id}")

        # Unique slug
        base = f"{city}-{state}-{date.isoformat() if date else 'undated'}-{ev.id}"
        slug = slugify(base)[:220] or f"event-{ev.id}"

        # Create as NOT public so it won't appear on public Media page
        MediaAlbum.objects.create(
            show=ev,
            title=title,
            slug=slug,
            city=city,
            state=state,
            date=date,
            is_public=False,   # <-- key part
            sort=999,          # optional: push to bottom if ever made public later
        )
        created += 1

    if created:
        messages.success(request, f"Created {created} missing Media Albums (kept private).")
    else:
        messages.info(request, "All events already have Media Albums. Nothing to backfill.")

    return redirect("control:media_submissions_list")

@is_super
def media_albums_list(request):
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "all").strip()  # all/public/private

    qs = (MediaAlbum.objects
          .select_related("show", "cover_item")
          .annotate(item_count=Count("items"))
          .order_by("-date", "-id"))

    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(city__icontains=q) |
            Q(state__icontains=q) |
            Q(show__name__icontains=q)
        )

    if status == "public":
        qs = qs.filter(is_public=True)
    elif status == "private":
        qs = qs.filter(is_public=False)

    return render(request, "controlpanel/media_albums_list.html", {
        "albums": qs[:500],
        "q": q,
        "status": status,
    })

@is_super
def media_album_edit(request, pk):
    album = get_object_or_404(MediaAlbum, pk=pk)

    if request.method == "POST" and request.POST.get("action") in ("save", "delete"):
        form = MediaAlbumForm(request.POST, instance=album)
        if request.POST.get("action") == "delete":
            album.delete()
            messages.success(request, "Album deleted.")
            return redirect("control:media_albums_list")

        if form.is_valid():
            form.save()
            messages.success(request, "Album saved.")
            return redirect("control:media_album_edit", album.id)
        else:
            messages.error(request, "Could not save album. Check the form.")
    else:
        form = MediaAlbumForm(instance=album)

    items = album.items.all().order_by("sort", "id")
    add_form = MediaItemAddForm()

    return render(request, "controlpanel/media_album_edit.html", {
        "album": album,
        "form": form,
        "items": items,
        "add_form": add_form,
    })

@is_super
@require_POST
def media_item_add(request, album_id):
    album = get_object_or_404(MediaAlbum, pk=album_id)

    add_form = MediaItemAddForm(request.POST, request.FILES)
    if not add_form.is_valid():
        form = MediaAlbumForm(instance=album)
        items = album.items.all().order_by("sort", "id")
        messages.error(request, "Could not add media item. Fix the errors below.")
        return render(request, "controlpanel/media_album_edit.html", {
            "album": album,
            "form": form,
            "items": items,
            "add_form": add_form,
        })

    kind = add_form.cleaned_data["kind"]
    caption = add_form.cleaned_data.get("caption") or ""
    sort = add_form.cleaned_data.get("sort") or 0
    url = (add_form.cleaned_data.get("url") or "").strip()
    images = add_form.cleaned_data.get("images") or []  # ✅ list

    if kind == "photo":
        for i, img in enumerate(images):
            MediaItem.objects.create(
                album=album,
                kind="photo",
                image=img,
                caption=caption,
                sort=sort + i,
            )
        messages.success(request, f"Added {len(images)} photo(s).")
        return redirect("control:media_album_edit", album.id)

    MediaItem.objects.create(
        album=album,
        kind="video",
        url=url,
        caption=caption,
        sort=sort,
    )
    messages.success(request, "Added video.")
    return redirect("control:media_album_edit", album.id)


@is_super
def media_item_delete(request, album_id, item_id):
    album = get_object_or_404(MediaAlbum, pk=album_id)
    it = get_object_or_404(MediaItem, pk=item_id, album=album)

    if request.method == "POST":
        if it.image:
            it.image.delete(save=False)
        it.delete()
        messages.warning(request, "Media item deleted.")

    return redirect("control:media_album_edit", pk=album.id)

@is_super
def media_album_toggle_public(request, pk):
    album = get_object_or_404(MediaAlbum, pk=pk)
    if request.method == "POST":
        album.is_public = not album.is_public
        album.save(update_fields=["is_public"])
        messages.success(request, f"Album is now {'PUBLIC' if album.is_public else 'PRIVATE'}.")
    return redirect("control:media_albums_list")

@is_super
def media_item_edit(request, album_id, item_id):
    album = get_object_or_404(MediaAlbum, pk=album_id)
    it = get_object_or_404(MediaItem, pk=item_id, album=album)

    form = MediaItemForm(request.POST or None, request.FILES or None, instance=it)

    if request.method == "POST":
        action = request.POST.get("action") or "save"

        if action == "save":
            if form.is_valid():
                obj = form.save(commit=False)

                # If they uploaded a new image, optionally delete the old file
                # NOTE: Django won't delete the old file automatically.
                if "image" in request.FILES and it.image:
                    it.image.delete(save=False)

                obj.save()
                messages.success(request, "Media item updated.")
                return redirect("control:media_album_edit", pk=album.id)
            messages.error(request, "Fix the errors and try again.")

        elif action == "delete_image":
            if it.image:
                it.image.delete(save=False)
                it.image = None
                it.save(update_fields=["image"])
                messages.warning(request, "Image removed.")
            return redirect("control:media_item_edit", album_id=album.id, item_id=it.id)

    return render(request, "controlpanel/media_item_edit.html", {
        "album": album,
        "item": it,
        "form": form,
    })




