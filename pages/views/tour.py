from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from ..models import Artist, ArtistPhoto, ArtistVideo
from ..forms import ArtistEPKForm, ArtistVideoForm, ArtistPhotoUploadForm

def tour(request):
    return render(request, 'pages/tour.html')

def tour_home(request):
    return render(request, "tour/home.html")

def tour_headliners(request):
    artists = Artist.objects.filter(is_public=True)
    return render(request, "tour/headliners.html", {"artists": artists})

def tour_epk_detail(request, slug):
    artist = get_object_or_404(Artist, slug=slug, is_public=True)
    return render(request, "tour/epk_detail.html", {"a": artist})

@login_required(login_url="/admin/login/")
def tour_epk_edit_self(request):
    # map logged-in user to their Artist row
    try:
        artist = Artist.objects.get(user=request.user)
    except Artist.DoesNotExist:
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

        # Add a video if provided
        if vid_form.is_valid() and vid_form.cleaned_data.get("url"):
            v = vid_form.save(commit=False)
            v.artist = artist
            v.save()
            messages.success(request, "Video added.")
        elif request.POST.get("url", "").strip():
            ok = False
            messages.error(request, "Invalid video link.")

        # Handle multiple photo uploads
        if photos_form.is_valid():
            for f in photos_form.files.getlist("new_photos"):
                ArtistPhoto.objects.create(artist=artist, image=f)
            if photos_form.files.getlist("new_photos"):
                messages.success(request, "Photos uploaded.")

        if ok:
            return redirect("tour_epk_edit_self")
    else:
        epk_form = ArtistEPKForm(instance=artist)
        vid_form = ArtistVideoForm()
        photos_form = ArtistPhotoUploadForm()

    # existing media lists
    photos = artist.photos.all()
    videos = artist.videos.all()

    return render(request, "tour/epk_edit.html", {
        "a": artist, "epk_form": epk_form, "vid_form": vid_form, "photos_form": photos_form,
        "photos": photos, "videos": videos
    })

def tour_media(request):
    return render(request, "tour/media.html")

def tour_shows(request):
    return render(request, "tour/shows.html")