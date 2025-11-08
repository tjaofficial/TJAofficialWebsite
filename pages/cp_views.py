from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Count, Sum, Case, When, IntegerField
from .models import Artist
from django import forms
from django.utils import timezone
from datetime import timedelta
from pages.models import Artist
from tickets.models import Ticket
from events.models import ArtistSaleLink, ArtistLinkHit, EventArtist

is_super = user_passes_test(lambda u: u.is_superuser)

class ArtistCPForm(forms.ModelForm):
    # Add a headliner/opener selector at the Artist level as a DEFAULT preference (optional)
    ROLE_CHOICES = [("headliner","Headliner"), ("opener","Opener"), ("guest","Guest")]
    default_role = forms.ChoiceField(choices=ROLE_CHOICES, required=False, initial="opener",
                                     help_text="Default role suggestion when assigning to events")

    class Meta:
        model = Artist
        fields = [
            "name","short_tag","genre","hometown","bio","avatar","hero_image","is_public","sort",
            "website_url","instagram_url","tiktok_url","youtube_url","spotify_url","apple_url","contact_email",
        ]

@is_super
def artist_list(request):
    q = (request.GET.get("q") or "").strip()
    active = (request.GET.get("public") or "").strip()  # yes/no/""
    qs = Artist.objects.all().order_by("sort","name")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(genre__icontains=q) | Q(hometown__icontains=q)
                       | Q(contact_email__icontains=q))
    if active == "yes":
        qs = qs.filter(is_public=True)
    elif active == "no":
        qs = qs.filter(is_public=False)

    return render(request, "pages_cp/artist_list.html", {
        "rows": qs,
        "q": {"q": q, "public": active},
    })

@is_super
def artist_add(request):
    form = ArtistCPForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("control:pages:artist_list")
    return render(request, "pages_cp/artist_form.html", {"form": form, "mode": "add"})

@login_required
def artist_edit(request, pk):
    obj = get_object_or_404(Artist, pk=pk)
    form = ArtistCPForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        if request.user == obj.user:
            return redirect("control:pages:artist_dashboard", obj.id)
        else:
            return redirect("control:pages:artist_list")
    return render(request, "pages_cp/artist_form.html", {"form": form, "mode": "edit", "artist": obj})

@login_required
def artist_dashboard(request, artist_id):
    artist = get_object_or_404(Artist, pk=artist_id)

    # --- Totals across all events ---
    base = Ticket.objects.filter(sold_by_artist_id=artist.id)
    total_sold = base.count()
    card_sold = base.filter(payment_method="card").count()
    cash_sold = base.filter(payment_method="cash").count()
    comp_sold = base.filter(payment_method="comp").count()

    # --- Top events (by total sold) ---
    # Group by event via ticket_type__event
    per_event = (
        base.values("ticket_type__event_id",
                    "ticket_type__event__name",
                    "ticket_type__event__start")
            .annotate(
                sold=Count("id"),
                card=Sum(Case(When(payment_method="card", then=1), default=0, output_field=IntegerField())),
                cash=Sum(Case(When(payment_method="cash", then=1), default=0, output_field=IntegerField())),
                comp=Sum(Case(When(payment_method="comp", then=1), default=0, output_field=IntegerField())),
            )
            .order_by("-sold", "ticket_type__event__start")
    )

    # --- Conversion by link (per assigned event) ---
    # For each ArtistSaleLink of this artist, show hits vs. sales
    links = ArtistSaleLink.objects.filter(artist_id=artist.id).select_related("event")
    conv_rows = []
    # optional time window filter
    days = int(request.GET.get("days", 90) or 90)
    since = timezone.now() - timedelta(days=days)
    for link in links:
        hits = link.hits.filter(at__gte=since).count()
        # sales attributed to ARTIST for that EVENT (card/cash/comp)
        sales_qs = base.filter(ticket_type__event_id=link.event_id, issued_at__gte=since)
        sales_total = sales_qs.count()
        slot_id = EventArtist.objects.get(event=link.event_id, artist=request.user.artist_dashboard).id
        conv_rows.append({
            "event_id": link.event_id,
            "event_name": link.event.name,
            "event_start": link.event.start,
            "token": link.token,
            "hits": hits,
            "sales": sales_total,
            "rate": (sales_total / hits * 100.0) if hits else None,
            "slot_id": slot_id,
        })

    # --- Recent 30-day timeline (simple counts per day) ---
    days_back = 30
    day0 = timezone.localdate()
    # Build a dict date->count for speed
    recent_qs = base.filter(issued_at__date__gte=day0 - timedelta(days=days_back-1))\
                    .values("issued_at__date")\
                    .annotate(c=Count("id"))
    cnt_by_date = {row["issued_at__date"]: row["c"] for row in recent_qs}
    timeline = [{"date": day0 - timedelta(days=i), "count": cnt_by_date.get(day0 - timedelta(days=i), 0)}
                for i in range(days_back)]
    timeline.reverse()

    ctx = {
        "artist": artist,
        "kpi": {
            "total": total_sold,
            "card": card_sold,
            "cash": cash_sold,
            "comp": comp_sold,
        },
        "per_event": per_event,      # list of dicts
        "conv_rows": conv_rows,      # list with hits/sales/rate
        "since": since,
        "days": days,
        "timeline": timeline,        # [{date, count}]
    }
    return render(request, "pages_cp/artist_dashboard.html", ctx)