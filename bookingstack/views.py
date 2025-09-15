from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from .models import *
from events.models import Venue
from django.utils.html import escape
from datetime import timedelta
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.core.management import call_command
from django.conf import settings

is_staff = user_passes_test(lambda u: u.is_active and u.is_staff)

def dashboard(request):
    pending = Outreach.objects.filter(reply_received=False).order_by("-sent_at")[:30]
    recent_epk = EpkVisit.objects.order_by("-opened_at")[:30]
    return render(request, "bookingstack/dashboard.html", {
        "pending_outreach": pending,
        "recent_epk": recent_epk,
    })

def venue_list(request):
    q = (request.GET.get("q") or "").strip()
    qs = Venue.objects.all()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(city__icontains=q))
    return render(request, "bookingstack/venue_list.html", {"venues": qs.order_by("name")[:500], "q": q})

def venue_detail(request, venue_id):
    v = get_object_or_404(Venue, id=venue_id)
    profile = getattr(v, "booking_profile", None) or VenueProfile.objects.filter(venue=v).first()
    contacts = v.booking_contacts.all() if hasattr(v, "booking_contacts") else VenueContact.objects.filter(venue=v)
    outreach = v.outreach.order_by("-sent_at")[:20] if hasattr(v, "outreach") else Outreach.objects.filter(venue=v).order_by("-sent_at")[:20]
    return render(request, "bookingstack/venue_detail.html", {"venue": v, "profile": profile, "contacts": contacts, "outreach": outreach})

def compose_pitch(request, venue_id):
    v = get_object_or_404(Venue, id=venue_id)
    # Pull artist info to auto-fill (from your existing Artist model)
    from pages.models import Artist  # adjust if Artist lives elsewhere
    artist = Artist.objects.filter(user=request.user).first() or Artist.objects.first()

    subject = f"{artist.name if artist else 'TJA'} – routing {getattr(v, 'city', '')} dates & live fan map"
    epk_url = request.build_absolute_uri(f"/booking/epk/{v.id}/")
    body = (
        f"Hi {(getattr(v, 'booking_profile', None) and v.booking_profile.booking_name) or 'there'},\n\n"
        f"I’m {artist.name if artist else 'TJA'} ({artist.genre if artist else 'pop/alt'} – {artist.hometown if artist else 'Detroit'}). "
        f"We’re routing through {getattr(v, 'city', 'your city')} and would love to play {getattr(v, 'name', 'your venue')}.\n"
        f"Windows: [put dates]\n\n"
        f"Proof of draw (live data): {epk_url}\n"
        f"Live vid: [link]  •  Tech: stage plot/rider in EPK\n\n"
        f"Thanks for considering!\n– {artist.name if artist else 'TJA'}\n"
    )
    return render(request, "bookingstack/compose_pitch.html", {"venue": v, "subject": subject, "body": body})

def public_epk(request, venue_id):
    v = get_object_or_404(Venue, id=venue_id)
    session_id = request.session.session_key or (request.session.save() or request.session.session_key)
    EpkVisit.objects.create(
        venue=v,
        session_id=session_id,
        referrer=request.META.get("HTTP_REFERER",""),
        ip=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT","")
    )
    assets = TechAsset.objects.order_by("-created_at")

    # Fan metrics: auto-detect by venue.city but allow override via ?city=
    city_param = (request.GET.get("city") or getattr(v, "city", "") or "").strip()
    city = city_param if city_param else ""
    snapshot = None
    if city:
        snapshot = (SocialMetricSnapshot.objects
                    .filter(city__iexact=city)
                    .order_by("-created_at")
                    .first())

    # Dropdown cities = distinct cities with snapshots
    cities = (SocialMetricSnapshot.objects
              .values_list("city", flat=True)
              .distinct()
              .order_by("city"))

    fan_votes = FanSupport.objects.filter(venue=v).count()

    from pages.models import Artist
    artist = Artist.objects.filter(user=request.user).first() or Artist.objects.first()
    return render(request, "bookingstack/public_epk.html", {
        "venue": v, "assets": assets, "artist": artist,
        "snapshot": snapshot, "cities": cities, "city": city,
        "fan_votes": fan_votes,
    })

@require_POST
def fan_vote(request, venue_id):
    v = get_object_or_404(Venue, id=venue_id)
    FanSupport.objects.create(
        venue=v,
        name=request.POST.get("name",""),
        email=request.POST.get("email",""),
        postal_code=request.POST.get("postal_code","")
    )
    return redirect("control:bookingstack:public_epk", venue_id=v.id)

def followup_queue(request):
    now = timezone.now()
    due = Outreach.objects.filter(reply_received=False, next_followup_at__lte=now).order_by("next_followup_at")
    return render(request, "bookingstack/followup_queue.html", {"due": due})

@require_POST
def create_inquiry(request, venue_id):
    v = get_object_or_404(Venue, id=venue_id)
    hard_date = request.POST.get("hard_date") or None
    ts = request.POST.get("target_start") or None
    te = request.POST.get("target_end") or None
    expected = request.POST.get("expected_draw") or None

    si = ShowInquiry.objects.create(
        venue=v,
        hard_date=hard_date or None,
        target_start=ts or None,
        target_end=te or None,
        expected_draw=int(expected) if expected else None,
        status="pending"
    )
    # Redirect back to EPK to show confirmation
    return redirect("control:bookingstack:public_epk", venue_id=v.id)

@require_POST
def refine_pitch(request, venue_id):
    v = get_object_or_404(Venue, id=venue_id)
    subject = request.POST.get("subject", "")
    body = request.POST.get("body", "")
    # Pull a bit more context
    from pages.models import Artist
    artist = Artist.objects.filter(user=request.user).first() or Artist.objects.first()
    city = getattr(v, "city", "") or "your city"

    # === Stub “AI” — deterministic polish you can replace with an LLM later ===
    refined_subject = subject.replace("routing", "routing / strong local draw")
    refined_body = (
        f"{body.strip()}\n\n"
        f"P.S. We’ve seen solid interest in {city}. Our live fan map shows measurable Spotify/IG/TikTok audience here, "
        f"and we’ll collaborate on promo (reels, paid geo-boost, email list). Happy to target a support slot if that’s best fit."
    )

    return render(request, "bookingstack/compose_pitch.html", {
        "venue": v,
        "subject": refined_subject,
        "body": refined_body,
        "refined": True,
    })

def venue_openers(request, venue_id):
    v = get_object_or_404(Venue, id=venue_id)
    openers = OpenerMap.objects.filter(venue=v).order_by("artist_name")
    return render(request, "bookingstack/venue_openers.html", {"venue": v, "openers": openers})

@require_POST
def add_contact(request, venue_id):
    v = get_object_or_404(Venue, id=venue_id)
    VenueContact.objects.create(
        venue=v,
        name=request.POST.get("name",""),
        role=request.POST.get("role",""),
        email=request.POST.get("email",""),
        phone=request.POST.get("phone",""),
        is_primary=bool(request.POST.get("is_primary")),
    )
    return redirect("control:bookingstack:venue_detail", venue_id=v.id)

@require_POST
def mark_reply_received(request, pk):
    o = get_object_or_404(Outreach, pk=pk)
    o.reply_received = True
    o.save(update_fields=["reply_received"])
    return redirect("control:bookingstack:venue_detail", venue_id=o.venue_id)

@require_POST
def bump_followup(request, venue_id):
    weeks = int(request.POST.get("weeks","2"))
    latest = Outreach.objects.filter(venue_id=venue_id).order_by("-sent_at").first()
    if latest:
        latest.next_followup_at = timezone.now() + timedelta(weeks=weeks)
        latest.save(update_fields=["next_followup_at"])
    return redirect("control:bookingstack:venue_detail", venue_id=venue_id)

@is_staff
def ops_refresh_metrics(request):
    if request.method == "POST":
        city   = (request.POST.get("city") or "").strip()
        radius = int(request.POST.get("radius") or 80)
        try:
            if city:
                call_command("refresh_social_metrics", city=city, radius=radius)
                messages.success(request, f"Social metrics refreshed for {city} (±{radius}km).")
            else:
                call_command("refresh_social_metrics", radius=radius)
                messages.success(request, f"Social metrics refreshed (default cities, ±{radius}km).")
        except Exception as e:
            messages.error(request, f"Failed to refresh metrics: {e}")
    return redirect("control:events:venues")

@is_staff
def ops_scrape_lineups(request):
    if request.method == "POST":
        try:
            call_command("scrape_lineups")
            messages.success(request, "Lineups scraper ran (stub).")
        except Exception as e:
            messages.error(request, f"Scrape failed: {e}")
    return redirect("control:events:venues")

@is_staff
def ops_remind_followups(request):
    if request.method == "POST":
        try:
            call_command("remind_followups")
            messages.success(request, "Follow-up reminders computed (see console/logs).")
        except Exception as e:
            messages.error(request, f"Reminder run failed: {e}")
    return redirect("control:events:venues")

@is_staff
def ops_backfill_profiles(request):
    if request.method == "POST":
        try:
            call_command("backfill_venue_profiles")
            messages.success(request, "Backfill complete for VenueProfile (deduped/created).")
        except Exception as e:
            messages.error(request, f"Backfill failed: {e}")
    return redirect("control:events:venues")



