from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from ..models import Artist, ArtistPhoto, ArtistVideo
from ..forms import ArtistEPKForm, ArtistVideoForm, ArtistPhotoUploadForm
from django.utils import timezone
from events.models import Event
from pages.models import Artist, Release, Video, Subscriber
from django.db.models import Exists, OuterRef, Prefetch, Min
from tickets.models import TicketType
import re, random

_YT_PATTERNS = [
    re.compile(r"[?&]v=([A-Za-z0-9_-]{6,})"),      # watch?v=
    re.compile(r"youtu\.be/([A-Za-z0-9_-]{6,})"),  # youtu.be/
    re.compile(r"/embed/([A-Za-z0-9_-]{6,})"),     # /embed/
]

def _youtube_id_from_url(url: str) -> str:
    u = url or ""
    for pat in _YT_PATTERNS:
        m = pat.search(u)
        if m:
            return m.group(1)
    return ""

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
    #---------------------------------------------------------------
    #------------------ VIDEOS -------------------------------------
    #---------------------------------------------------------------
    headliner_ids = [a.id for a in headliners]
    headliner_videos = list(
        ArtistVideo.objects.filter(artist_id__in=headliner_ids).select_related("artist").order_by("sort", "id")[:48]
    )
    artist_payload = []
    for av in headliner_videos:
        vid = _youtube_id_from_url(av.url)
        if vid:
            artist_payload.append({
                "title": av.title or av.artist.name,
                "youtube_id": vid,
                "artist": av.artist.name,
                "artist_slug": av.artist.slug,
            })
    random.shuffle(artist_payload)
    reel = artist_payload[:6]

    stats = {
        "dates": shows.count(),
        "cities": len({(s.venue.city, s.venue.state) for s in shows}),
        "headliners": len(headliners),
    }

    return render(request, "tour/home.html", {
        "headliners": headliners,
        "shows": shows,
        "releases": releases,
        "reel": reel,
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
    artists = Artist.objects.filter(is_public=True, default_role="headliner")
    return render(request, "tour/headliners.html", {"artists": artists})

def tour_openers(request):
    artists = Artist.objects.filter(is_public=True, default_role="opener")
    return render(request, "tour/openers.html", {"artists": artists})

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

def presskit_daynnight(request):
    context = {
        "tour_window": "Jan 30 – May 31, 2026",
        "corktown_stat": "120 tickets sold, 150 Capacity",
        "contact_phone": "(810) 618-2253",
        "contact_email": "tjaofficialbooking@gmail.com",
        "site_url": "https://www.tjaofficial.com",
        "artists": [
            {
                "name": "TJA",
                "slug": "tja",
                "desc": "High-energy Catchy hip-hop/alt fusion. Michigan-built. Crowd-engaging sets.",
                "socials": {"IG": "@tjaofficial"},
            },
            {
                "name": "Jay Willy",
                "slug": "jay-willy",
                "desc": "Punchy hooks, upbeat bounce, versatile stage presence.",
                "socials": {"IG": "@jaywilly"},
            },
            {
                "name": "Toxic Reality",
                "slug": "toxic-reality",
                "desc": "Dark-toned alt vibes with live-show intensity.",
                "socials": {"IG": "@toxicreality"},
            },
        ],
        "tech_requirements": [
            "House Audio System",
            "2x DI boxes (stereo playback + backup)(Only with band)",
            "Basic stage wash (we can adapt to room with our own lights)",
        ],
        "promo_reel_url": "",  # optional: MP4 or YouTube embed
        "hero_image_url": "/static/img/full_tour_logo.png",  # optional: hosted hero image
        "media_gallery": [
            "/static/img/promo1.png",
            "/static/img/promo2.jpeg",
            "/static/img/promo3.png",
            "/static/img/promo4.png",
            "/static/img/promo5.jpeg",
            "/static/img/promo6.jpeg",
        ]
    }
    return render(request, "presskit/presskit_daynnight.html", context)



