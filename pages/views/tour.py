from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from ..models import Artist, ArtistPhoto
from ..forms import ArtistEPKForm, ArtistVideoForm, ArtistPhotoUploadForm
from django.utils import timezone
from events.models import Event
from pages.models import Artist, Release, Video, Subscriber
from django.db.models import Exists, OuterRef, Prefetch, Min
from tickets.models import TicketType

def tour(request):
    return render(request, 'pages/tour.html')

def tour_home(request):
    now = timezone.now()

    # Headliners (up to 6 to fill the stagger grid)
    headliners = (Artist.objects
                  .filter(is_public=True, default_role="headliner")
                  .order_by("sort", "name")
                  .only("id", "slug", "name", "short_tag", "genre", "hometown", "avatar")
                 )[:6]
    
    active_types = TicketType.objects.filter(active=True, name="General Admission").order_by('price_cents', 'sales_start')
    # Next 12 shows
    shows = (Event.objects
                .filter(start__date__gte=now, is_tour_stop=True)
                .order_by("start")[:12]
                .select_related("venue")
                .prefetch_related(Prefetch("ticket_types", queryset=active_types, to_attr="prefetched_types"))
                .annotate(
                    has_tickets=Exists(
                        TicketType.objects.filter(event_id=OuterRef("pk"), active=True)
                    ),
                    # Example: the earliest sales_end across all TTs for this event
                    first_sales_end=Min("ticket_types__sales_end")
                )
            )

    # Latest releases & videos
    releases = (Release.objects
                .filter(is_public=True)
                .order_by("-release_date", "-id")[:6])
    
    videos = (Video.objects
              .filter(is_public=True)
              .order_by("sort", "-published_at", "-id")[:6])

    stats = {
        "dates": shows.count(),
        "cities": len({(s.venue.city, s.venue.state) for s in shows}),
        "headliners": len(headliners),
    }

    return render(request, "tour/home.html", {
        "headliners": headliners,
        "shows": shows,
        "releases": releases,
        "videos": videos,
        "stats": stats,
        "tour_hashtag": "#DayNNightTour",
    })


def tour_subscribe(request):
    if request.method != "POST":
        return redirect("tour_home")
    email = (request.POST.get("email") or "").strip().lower()
    name  = (request.POST.get("name")  or "").strip()
    if not email:
        messages.error(request, "Enter your email to subscribe.")
        return redirect("tour_home")
    sub, created = Subscriber.objects.get_or_create(email=email, defaults={
        "name": name,
        "source": "/tour/",
        "consent": True,
        "ip": request.META.get("REMOTE_ADDR"),
        "user_agent": request.META.get("HTTP_USER_AGENT","")[:500],
    })
    if not created and name and not sub.name:
        sub.name = name
        sub.save(update_fields=["name"])
    messages.success(request, "You're on the list. See you on tour!")
    return redirect("tour_home")

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