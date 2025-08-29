from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden, JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from ..models import Artist, ArtistPhoto, ArtistVideo
from ..forms import ArtistEPKForm, ArtistVideoForm, ArtistPhotoUploadForm

def _artist_for_user(user):
    try:
        return Artist.objects.get(user=user)
    except Artist.DoesNotExist:
        return None

@login_required
def tour_epk_edit_self(request):
    artist = _artist_for_user(request.user)
    if not artist:
        return HttpResponseForbidden("No EPK assigned to this user.")

    if request.method == "POST":
        epk_form = ArtistEPKForm(request.POST, request.FILES, instance=artist)
        vid_form = ArtistVideoForm(request.POST or None)
        photos_form = ArtistPhotoUploadForm(request.POST, request.FILES)

        ok = True
        if epk_form.is_valid():
            epk_form.save()
            messages.success(request, "Profile updated.")
        else:
            ok = False

        if vid_form.is_valid() and vid_form.cleaned_data.get("url"):
            v = vid_form.save(commit=False)
            v.artist = artist
            v.save()
            messages.success(request, "Video added.")
        elif request.POST.get("url", "").strip():
            ok = False
            messages.error(request, "Invalid video link.")

        if photos_form.is_valid():
            uploaded = photos_form.files.getlist("new_photos")
            for f in uploaded:
                ArtistPhoto.objects.create(artist=artist, image=f)
            if uploaded:
                messages.success(request, f"Uploaded {len(uploaded)} photo(s).")

        if ok:
            return redirect("tour_epk_edit_self")
    else:
        epk_form = ArtistEPKForm(instance=artist)
        vid_form = ArtistVideoForm()
        photos_form = ArtistPhotoUploadForm()

    return render(request, "tour/epk_edit.html", {
        "a": artist,
        "epk_form": epk_form,
        "vid_form": vid_form,
        "photos_form": photos_form,
        "photos": artist.photos.all(),
        "videos": artist.videos.all(),
    })

@login_required
def tour_photo_delete(request, pk):
    artist = _artist_for_user(request.user)
    if not artist: return HttpResponseForbidden("No EPK assigned.")
    if request.method != "POST": return HttpResponseBadRequest("POST required")
    p = get_object_or_404(ArtistPhoto, pk=pk, artist=artist)
    p.delete()
    messages.success(request, "Photo removed.")
    return redirect("tour_epk_edit_self")

@login_required
def tour_video_delete(request, pk):
    artist = _artist_for_user(request.user)
    if not artist: return HttpResponseForbidden("No EPK assigned.")
    if request.method != "POST": return HttpResponseBadRequest("POST required")
    v = get_object_or_404(ArtistVideo, pk=pk, artist=artist)
    v.delete()
    messages.success(request, "Video removed.")
    return redirect("tour_epk_edit_self")
