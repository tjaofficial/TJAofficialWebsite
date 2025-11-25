# setbuilder/views_control.py
from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import transaction
from django.contrib import messages
from .forms import SongForm
from django.db.models import Q
from pages.models import Artist  # your Artist model
from .models import Song, ShowSet, ShowItem

def is_headliner(u):
    if not u.is_authenticated:
        return False
    return Artist.objects.filter(user=u, is_public=True).exists() or u.is_superuser

headliner_required = user_passes_test(is_headliner)

# ---------- Songs CRUD ----------
@headliner_required
def my_songs(request):
    my_artist = Artist.objects.filter(user=request.user).first()
    qs = Song.objects.filter(Q(primary_artist=my_artist) | Q(collaborator_artists=my_artist)).distinct()
    return render(request, "setbuilder/songs_list.html", {"songs": qs, "my_artist": my_artist})

@headliner_required
def song_new(request):
    my_artist = Artist.objects.filter(user=request.user).first()
    form = SongForm(
        request.POST or None, 
        initial={"primary_artist": my_artist}
    )
    form.fields["primary_artist"].queryset = Artist.objects.filter(Q(user=request.user)|Q(default_role="headliner"))
    print(form.errors)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Song added.")
        return redirect("control:setbuilder:songs")
    return render(request, "setbuilder/song_form.html", {
        "form": form, 
        "mode":"new"
    })

@headliner_required
def song_edit(request, pk):
    obj = get_object_or_404(Song, pk=pk)
    form = SongForm(request.POST or None, instance=obj)
    form.fields["primary_artist"].queryset = Artist.objects.filter(Q(user=request.user)|Q(default_role="headliner"))
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Song updated.")
        return redirect("control:setbuilder:songs")
    return render(request, "setbuilder/song_form.html", {"form": form, "mode":"edit", "song": obj})

@headliner_required
def song_delete(request, pk):
    obj = get_object_or_404(Song, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Song deleted.")
    return redirect("control:setbuilder:songs")

# ---------- Build a show ----------
@headliner_required
def build_show(request, slug=None):
    my_artist = Artist.objects.filter(user=request.user).first()
    editing = None
    items = []
    if slug:
        editing = get_object_or_404(ShowSet, slug=slug)
        items = list(editing.items.select_related("artist","song").all())
    headliners = Artist.objects.filter(default_role="headliner", is_public=True).order_by("sort","name")
    openers = Artist.objects.filter(default_role="opener", is_public=True).order_by("sort","name")
    return render(request, "setbuilder/build_show.html", {
        "editing": editing,
        "items": items,
        "headliners": headliners,
        "openers": openers,
        "my_artist": my_artist,
    })

@headliner_required
@transaction.atomic
def save_show(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    import json
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Bad JSON")

    label = (payload.get("label") or "").strip()
    vibe = (payload.get("vibe") or "mixed")
    items = payload.get("items") or []
    slug = payload.get("slug") or None

    if not label:
        return HttpResponseBadRequest("Label required")

    if slug:
        print("CHECK 2")
        show = get_object_or_404(ShowSet, slug=slug)
        show.label = label
        show.vibe = vibe
        show.save(update_fields=["label","vibe"])
        show.items.all().delete()
    else:
        print("CHECK 2")
        show = ShowSet.objects.create(label=label, vibe=vibe, created_by=request.user)

    # Recreate items in order
    for idx, it in enumerate(items):
        kind = it.get("kind")
        duration = int(it.get("duration_seconds") or 0)
        display_name = it.get("display_name") or ""
        artist_id = it.get("artist_id")
        song_id = it.get("song_id")

        ShowItem.objects.create(
            show=show,
            sort=idx,
            kind=kind,
            duration_seconds=max(0, duration),
            display_name=display_name[:200],
            artist_id=artist_id or None,
            song_id=song_id or None,
        )

    messages.success(request, "Show saved.")
    return JsonResponse({"ok": True, "slug": show.slug, "total_seconds": show.total_seconds(), "total_label": show.total_label()})

# ---------- Saved shows list ----------
@headliner_required
def shows_list(request):
    rows = ShowSet.objects.order_by("-created_at")
    return render(request, "setbuilder/shows_list.html", {"rows": rows})

# ---------- API helpers ----------
@headliner_required
def api_songs_by_artist(request, artist_id: int):
    songs = Song.objects.filter(Q(primary_artist_id=artist_id)|Q(collaborator_artists__id=artist_id)).distinct()
    data = [
        {"id": s.id, "title": s.title, "dur": s.duration_seconds, "label": s.duration_label}
        for s in songs
    ]
    return JsonResponse({"songs": data})
