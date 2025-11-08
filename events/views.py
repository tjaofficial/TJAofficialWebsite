from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from django.utils import timezone
from .utils import ensure_event_checklist
from .forms import EventForm, VenueForm, Event, TechPersonForm, EventTechAssignForm, EventMediaForm
from tickets.models import TicketType, TicketReservation, Ticket
from pages.models import Artist
from events.models import ArtistSaleLink
from django.db import transaction
import stripe
from datetime import timedelta
from django.views.decorators.http import require_POST
from django.conf import settings
from django.http import HttpResponseBadRequest, JsonResponse, HttpResponse
from django.db.models import Q, Sum, Exists, OuterRef, Prefetch, Min
from django.contrib import messages
from django.urls import reverse
from io import BytesIO
import qrcode

stripe.api_key = settings.STRIPE_SECRET_KEY
is_super = user_passes_test(lambda u: u.is_superuser)

def events_list(request):
    # --- Filters ---
    city  = (request.GET.get("city") or "").strip()
    state = (request.GET.get("state") or "").strip()
    venue = (request.GET.get("venue") or "").strip()
    show_past = (request.GET.get("past") in ("1", "true", "yes"))

    now = timezone.now()

    base = (Event.objects
            .filter(published=True)
            .select_related("venue")
            .annotate(has_tickets=Exists(
                TicketType.objects.filter(event_id=OuterRef("pk"), active=True)
            )))

    # Filter by related Venue fields
    if city:
        base = base.filter(venue__city__icontains=city)
    if state:
        base = base.filter(venue__state__icontains=state)
    if venue:
        base = base.filter(venue__name__icontains=venue)

    # Upcoming only (default) vs include past
    if not show_past:
        base = base.filter(start__gte=now)

    # Order: soonest first
    events = list(base.order_by("start"))

    # Hero: nearest future if available, else first available
    hero = None
    for e in events:
        if e.start and e.start >= now:
            hero = e
            break
    if not hero and events:
        hero = events[0]

    # Distinct filter options from Venues that have published events
    vqs = Venue.objects.filter(event__published=True)
    cities = (vqs.exclude(city="").exclude(city__isnull=True)
                  .values_list("city", flat=True).distinct().order_by("city"))
    states = (vqs.exclude(state="").exclude(state__isnull=True)
                  .values_list("state", flat=True).distinct().order_by("state"))
    venues = (vqs.exclude(name="").exclude(name__isnull=True)
                  .values_list("name", flat=True).distinct().order_by("name"))

    ctx = {
        "hero": hero,
        "events": events,
        "filters": {"city": city, "state": state, "venue": venue, "past": "1" if show_past else ""},
        "cities": cities, "states": states, "venues": venues,
    }
    return render(request, "events/list.html", ctx)

@is_super
def event_add(request):
    form = EventForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("control:events:list")
    return render(request, "events/event_form.html", {"form": form, "mode": "add"})

@is_super
def event_edit(request, pk):
    ev = get_object_or_404(Event, pk=pk)
    form = EventForm(request.POST or None, instance=ev)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("control:events:list")
    return render(request, "events/event_form.html", {"form": form, "mode": "edit", "ev": ev})

@login_required
def venues_list(request):
    qs = Venue.objects.order_by("name")
    return render(request, "events/venues_list.html", {"venues": qs})

@login_required
def venue_add(request):
    form = VenueForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("control:events:venues")
    return render(request, "events/venue_form.html", {"form": form})

@is_super
def event_tickets(request, pk):
    ev = get_object_or_404(Event, pk=pk)
    types = (TicketType.objects
             .filter(event=ev, active=True)
             .order_by("price_cents"))
    return render(request, "events/purchase.html", {"event": ev, "types": types})

@is_super
def create_checkout(request, pk):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    ev = get_object_or_404(Event, pk=pk)

    # parse quantities from POST like qty_<type_id>
    selections = []
    total_qty = 0
    purchaser_email = request.POST.get("email", "").strip()
    purchaser_name  = request.POST.get("purchaser_name", "").strip()
    for tt in TicketType.objects.filter(event=ev, active=True):
        qty = int(request.POST.get(f"qty_{tt.id}", 0) or 0)
        if qty > 0:
            selections.append({"tt": tt, "qty": qty})
            total_qty += qty
    if not selections:
        return HttpResponseBadRequest("No tickets selected.")

    # create a temporary placeholder session id to allow atomic holds
    holds = TicketReservation.create_reservations(
        selections, 
        purchaser_email=purchaser_email,
        purchaser_name=purchaser_name,
    )

    # build Stripe line items
    line_items = []
    for sel in selections:
        line_items.append({
            "quantity": sel["qty"],
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"{ev.name or 'Event'} — {sel['tt'].name}",
                },
                "unit_amount": sel["tt"].price_cents,
            },
        })

    metadata = {
        # store reservation ids to fulfill on webhook
        "reservation_ids": ",".join(str(h.id) for h in holds),
        "event_id": str(ev.id),
        "purchaser_email": purchaser_email,
        "purchaser_name": purchaser_name,
    }

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=line_items,
        success_url=f"{settings.SITE_BASE_URL}/control/events/tickets/success/?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.SITE_BASE_URL}/control/events/tickets/cancel/",
        metadata=metadata,
    )

    # persist the session id on the holds
    for h in holds:
        h.stripe_session_id = session.id
        h.save(update_fields=["stripe_session_id"])

    return redirect(session.url, permanent=False)

@is_super
def purchase_success(request):
    return render(request, "events/purchase_success.html")

@is_super
def purchase_cancel(request):
    return render(request, "events/purchase_cancel.html")

# --- Tech directory ---
@login_required
def tech_list(request):
    q = request.GET.get("q","").strip()
    role = request.GET.get("role","").strip()
    city = request.GET.get("city","").strip()
    state = request.GET.get("state","").strip()
    qs = TechPerson.objects.filter(active=True)
    if q:
        qs = qs.filter(Q(name__icontains=q)|Q(email__icontains=q)|Q(phone__icontains=q))
    if role:
        qs = qs.filter(role=role)
    if city:
        qs = qs.filter(city__icontains=city)
    if state:
        qs = qs.filter(state__iexact=state)
    return render(request, "events/tech_list.html", {"tech": qs, "q": {"q":q,"role":role,"city":city,"state":state}})

@login_required
def tech_add(request):
    form = TechPersonForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        form.save()
        return redirect("control:events:tech_list")
    return render(request, "events/tech_form.html", {"form":form, "mode":"add"})

@login_required
def tech_edit(request, pk):
    person = get_object_or_404(TechPerson, pk=pk)
    form = TechPersonForm(request.POST or None, instance=person)
    if request.method=="POST" and form.is_valid():
        form.save()
        return redirect("control:events:tech_list")
    return render(request, "events/tech_form.html", {"form":form, "mode":"edit", "person":person})

# --- Event tech assignments ---
@login_required
def event_tech_list(request, event_id):
    ev = get_object_or_404(Event, pk=event_id)
    assigns = ev.tech_assignments.select_related("person").all()
    return render(request, "events/event_tech_list.html", {"event": ev, "assigns": assigns})

@login_required
def event_tech_assign(request, event_id):
    ev = get_object_or_404(Event, pk=event_id)
    form = EventTechAssignForm(request.POST or None)
    form.fields["person"].queryset = TechPerson.objects.filter(active=True).order_by("name")
    if request.method=="POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.event = ev
        obj.save()
        return redirect("control:events:event_tech_list", event_id=ev.id)
    return render(request, "events/event_tech_form.html", {"event": ev, "form": form})

@is_super
def event_tech_remove(request, event_id, assign_id):
    ev = get_object_or_404(Event, pk=event_id)
    a = get_object_or_404(EventTechAssignment, pk=assign_id, event=ev)
    a.delete()
    return redirect("control:events:event_tech_list", event_id=ev.id)

# --- Event media ---
@login_required
def event_media_list(request, event_id):
    ev = get_object_or_404(Event, pk=event_id)
    media = ev.media.order_by("-uploaded_at")
    return render(request, "events/event_media_list.html", {"event": ev, "media": media})

@login_required
def event_media_add(request, event_id):
    ev = get_object_or_404(Event, pk=event_id)
    form = EventMediaForm(request.POST or None, request.FILES or None)
    if request.method=="POST" and form.is_valid():
        m = form.save(commit=False)
        m.event = ev
        m.save()
        return redirect("control:events:event_media", event_id=ev.id)
    return render(request, "events/event_media_form.html", {"event": ev, "form": form})

@is_super
def event_media_delete(request, event_id, media_id):
    ev = get_object_or_404(Event, pk=event_id)
    m = get_object_or_404(EventMedia, pk=media_id, event=ev)
    m.delete()
    return redirect("control:events:event_media", event_id=ev.id)

@login_required
def event_dashboard(request, event_id):
    ev = get_object_or_404(Event, pk=event_id)

    # Ticket stats
    ttypes = TicketType.objects.filter(event=ev)
    capacity = ttypes.aggregate(Sum("quantity"))["quantity__sum"] or 0
    sold = Ticket.objects.filter(ticket_type__event=ev).count()
    checked_in = Ticket.objects.filter(ticket_type__event=ev, checked_in_at__isnull=False).count()
    remaining = max(0, capacity - sold)

    # Assignments / equipment / media
    tech = ev.tech_assignments.select_related("person").order_by("person__name")
    gear = ev.equipment_assignments.select_related("equipment").order_by("equipment__category","equipment__name")
    media = ev.media.order_by("-uploaded_at")[:12]

    ctx = {
        "event": ev,
        "stats": {"capacity": capacity, "sold": sold, "remaining": remaining, "checked_in": checked_in},
        "tech": tech,
        "gear": gear,
        "media": media,
    }
    return render(request, "events/event_dashboard.html", ctx)

def event_artists(request, event_id):
    ev = get_object_or_404(Event, pk=event_id)
    slots = list(ev.artist_slots.select_related("artist").order_by("set_order","id"))

    # Per-artist counts for this event
    rows = []
    for s in slots:
        qs = Ticket.objects.filter(ticket_type__event=ev, sold_by_artist_id=s.artist_id)
        total = qs.count()
        card = qs.filter(payment_method="card").count()
        cash = qs.filter(payment_method="cash").count()
        rows.append({"slot": s, "total": total, "card": card, "cash": cash})
    return render(request, "events/event_artists.html", {"event": ev, "rows": rows})

@is_super
def event_artist_assign(request, event_id):
    ev = get_object_or_404(Event, pk=event_id)
    if request.method == "POST":
        artist_id = request.POST.get("artist")
        role = request.POST.get("role") or "opener"
        set_order = int(request.POST.get("set_order") or 0)
        a = get_object_or_404(Artist, id=artist_id)
        slot, created = EventArtist.objects.get_or_create(event=ev, artist=a, defaults={"role": role, "set_order": set_order})
        if not created:
            slot.role = role
            slot.set_order = set_order
            slot.save()
        ArtistSaleLink.objects.get_or_create(event=ev, artist=a)  # ensure link
        return redirect("control:events:event_artists", event_id=ev.id)

    artists = Artist.objects.filter(is_public=True).order_by("name")
    return render(request, "events/event_artist_assign.html", {"event": ev, "artists": artists})

@is_super
def event_artist_remove(request, event_id, slot_id):
    ev = get_object_or_404(Event, pk=event_id)
    slot = get_object_or_404(EventArtist, id=slot_id, event=ev)
    slot.delete()
    return redirect("control:events:event_artists", event_id=ev.id)

@login_required
def event_artist_link(request, event_id, slot_id):
    ev = get_object_or_404(Event, pk=event_id)
    slot = get_object_or_404(EventArtist.objects.select_related("artist"), id=slot_id, event=ev)
    link, _ = ArtistSaleLink.objects.get_or_create(event=ev, artist=slot.artist)
    base = request.build_absolute_uri("/").rstrip("/")
    # Public purchase page (see Section 3)
    purchase_url = f"{base}{reverse('control:tickets:public_purchase', args=[ev.id])}?artist={link.token}"
    return render(request, "events/event_artist_link.html", {
        "event": ev, "slot": slot, "link": link, "purchase_url": purchase_url
    })

@login_required
def artist_link_qr(request, event_id, token):
    base = request.build_absolute_uri("/").rstrip("/")
    purchase_url = f"{base}{reverse('control:tickets:public_purchase', args=[event_id])}?artist={token}"
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(purchase_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    from django.http import HttpResponse
    return HttpResponse(buf.getvalue(), content_type="image/png")

@login_required
def artist_cash_sale(request, event_id, artist_id):
    ev = get_object_or_404(Event, pk=event_id)
    artist = get_object_or_404(Artist, pk=artist_id)
    types = TicketType.objects.filter(event=ev, active=True).order_by("price_cents")

    if request.method == "POST":
        purchaser_name  = request.POST.get("purchaser_name","").strip()
        purchaser_email = request.POST.get("purchaser_email","").strip()
        selections = []
        for tt in types:
            qty = int(request.POST.get(f"qty_{tt.id}", 0) or 0)
            if qty > 0:
                selections.append((tt, qty))
        if not selections:
            messages.error(request, "Select at least one quantity.")
            return redirect(request.path)

        # inventory-safe issue
        from django.db import transaction
        created = []
        try:
            with transaction.atomic():
                lock_ids = [tt.id for tt,_ in selections]
                locked = TicketType.objects.select_for_update().filter(id__in=lock_ids, event=ev)
                tt_map = {t.id: t for t in locked}
                for tt, qty in selections:
                    tlocked = tt_map[tt.id]
                    if qty > tlocked.remaining():
                        raise ValueError(f"Not enough inventory for {tlocked.name}. Remaining: {tlocked.remaining()}")
                for tt, qty in selections:
                    tlocked = tt_map[tt.id]
                    for _ in range(qty):
                        created.append(Ticket.objects.create(
                            ticket_type=tlocked,
                            purchaser_name=purchaser_name,
                            purchaser_email=purchaser_email,
                            payment_method="cash",
                            sold_by_artist_id=artist.id,
                            sold_by_user=request.user,
                        ))
        except ValueError as e:
            messages.error(request, str(e))
            return redirect(request.path)

        messages.success(request, f"Issued {len(created)} cash tickets for {artist.name}.")
        return redirect("control:events:event_artists", event_id=ev.id)

    return render(request, "events/artist_cash_sale.html", {"event": ev, "artist": artist, "types": types})

def artist_link_redirect(request, token):
    link = get_object_or_404(ArtistSaleLink, token=token, enabled=True)
    # Log the hit
    ArtistLinkHit.objects.create(
        link=link,
        user_agent=request.META.get("HTTP_USER_AGENT","")[:300],
        referer=request.META.get("HTTP_REFERER",""),
    )
    # Send to public purchase page with ?artist=<token>
    target = reverse("control:tickets:public_purchase", args=[link.event_id])
    return redirect(f"{target}?artist={token}")

def checklist_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    cl = ensure_event_checklist(event)
    done, total = cl.progress()
    pct = round((done * 100 / total), 2) if total else 0.0
    return render(request, "events/checklist.html", {
        "event": event,
        "checklist": cl,
        "items": cl.items.select_related("completed_by", "assignee"),
        "done": done,
        "total": total,
        "pct": pct,
    })

@require_POST
def checklist_toggle(request, item_id):
    item = get_object_or_404(EventChecklistItem, pk=item_id, checklist__event__isnull=False)
    item.toggle(user=request.user)
    if request.headers.get("x-requested-with") == "fetch":
        d = item.checklist.items.filter(done_at__isnull=False).count()
        t = item.checklist.items.count()
        return JsonResponse({"ok": True, "done": d, "total": t, "is_done": item.is_done})
    return redirect("event_checklist", event_id=item.checklist.event_id)

def checklist_edit(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    cl = ensure_event_checklist(event)

    if request.method == "POST":
        # Simple editor: receive arrays of fields (title[], id[], order[], required[])
        ids = request.POST.getlist("id[]")
        titles = request.POST.getlist("title[]")
        orders = request.POST.getlist("order[]")
        requireds = request.POST.getlist("required[]")

        with transaction.atomic():
            seen = set()
            for i in range(len(titles)):
                title = (titles[i] or "").strip()
                if not title:
                    continue
                try:
                    _id = int(ids[i]) if ids[i] else None
                    order = int(orders[i]) if orders[i] else i
                    req = (requireds[i] == "1")
                except Exception:
                    _id, order, req = None, i, True

                if _id:
                    it = EventChecklistItem.objects.filter(pk=_id, checklist=cl).first()
                    if it:
                        it.title = title
                        it.order = order
                        it.is_required = req
                        it.save(update_fields=["title", "order", "is_required"])
                        seen.add(it.pk)
                else:
                    it = EventChecklistItem.objects.create(
                        checklist=cl, title=title, order=order, is_required=req
                    )
                    seen.add(it.pk)

            # delete removed rows
            cl.items.exclude(pk__in=seen).delete()

        return redirect("event_checklist", event_id=event.id)

    return render(request, "events/checklist_edit.html", {
        "event": event,
        "checklist": cl,
        "items": cl.items.all(),
    })

@require_POST
def checklist_reorder(request, event_id):
    """Optional: accept JSON {items:[{"id":1,"order":0},...]} for drag-n-drop."""
    import json
    event = get_object_or_404(Event, pk=event_id)
    cl = ensure_event_checklist(event)
    try:
        payload = json.loads(request.body.decode("utf-8"))
        items = payload.get("items", [])
    except Exception:
        return HttpResponseBadRequest("bad json")
    with transaction.atomic():
        for row in items:
            _id = int(row.get("id"))
            order = int(row.get("order"))
            EventChecklistItem.objects.filter(pk=_id, checklist=cl).update(order=order)
    return JsonResponse({"ok": True})

def event_ics(request, pk):
    e = get_object_or_404(Event.objects.select_related("venue"), pk=pk, published=True)
    if not e.start:
        return redirect("events_public:list")

    title = e.name or "Event"
    # Build a friendly location from Venue
    loc_parts = []
    if e.venue:
        if e.venue.name:  loc_parts.append(e.venue.name)
        if e.venue.city:  loc_parts.append(e.venue.city)
        if e.venue.state: loc_parts.append(e.venue.state)
    loc = ", ".join(loc_parts)

    desc = (getattr(e, "afterparty_info", "") or "")
    if getattr(e, "meet_greet_info", ""):
        desc = (desc + "\n\n" + e.meet_greet_info).strip()
    desc = desc.replace("\n", "\\n")

    dt    = e.start.strftime("%Y%m%dT%H%M%S")
    dt_end = e.end.strftime("%Y%m%dT%H%M%S") if e.end else ""

    ics = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//TJA//Events//EN",
        "BEGIN:VEVENT",
        f"UID:event-{e.pk}@tjaofficial.com",
        f"DTSTAMP:{timezone.now().strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART:{dt}",
    ]
    if dt_end:
        ics.append(f"DTEND:{dt_end}")
    ics.append(f"SUMMARY:{title}")
    if loc:
        ics.append(f"LOCATION:{loc}")
    if desc:
        ics.append(f"DESCRIPTION:{desc}")
    ics += ["END:VEVENT", "END:VCALENDAR"]

    resp = HttpResponse("\r\n".join(ics), content_type="text/calendar; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="event-{e.pk}.ics"'
    return resp


def event_details(request, event_id, slug=None):
    now = timezone.now()

    # Only show published events
    tt_qs = (TicketType.objects
             .filter(active=True)
             .order_by("price_cents", "sales_start"))

    event = (Event.objects
             .filter(id=event_id, published=True)
             .select_related("venue")
             .prefetch_related(Prefetch("ticket_types", queryset=tt_qs, to_attr="types_active"))
             .first())
    event = get_object_or_404(Event, id=event_id, published=True)

    # Fetch active ticket types (prefetched if using the queryset above)
    types = getattr(event, "types_active", None) or tt_qs.filter(event=event)

    # Compute sale state for the primary/general type + any others
    for t in types:
        t.is_on_sale = t.is_on_sale()
        t.remaining = t.remaining()

    any_on_sale = any((t.is_on_sale and t.remaining > 0) for t in types)

    # Pick hero image
    hero_src = event.cover_image.url if event.cover_image else (event.flyer.url if event.flyer else "")

    # Add-to-calendar: a simple ICS download URL (route below)
    ics_url = None
    if event.start:
        from django.urls import reverse
        ics_url = reverse("control:events:ics", args=[event.id])

    ctx = {
        "event": event,
        "types": types,
        "any_on_sale": any_on_sale,
        "hero_src": hero_src,
        "now": now,
        "ics_url": ics_url,
    }
    return render(request, "events/public_event_details.html", ctx)

def public_events(request):
    # --- Filters ---
    city  = (request.GET.get("city") or "").strip()
    state = (request.GET.get("state") or "").strip()
    venue = (request.GET.get("venue") or "").strip()
    show_past = (request.GET.get("past") in ("1", "true", "yes"))

    now = timezone.now()

    # Prefetch only active types to speed up template work
    active_types = TicketType.objects.filter(active=True, name="General Admission").order_by('price_cents', 'sales_start')

    base = (
        Event.objects
        .filter(published=True)
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

    # Filter by related Venue fields
    if city:
        base = base.filter(venue__city__icontains=city)
    if state:
        base = base.filter(venue__state__icontains=state)
    if venue:
        base = base.filter(venue__name__icontains=venue)

    # Upcoming only (default) vs include past
    if not show_past:
        base = base.filter(start__gte=now)

    # Order: soonest first
    events = list(base.order_by("start"))

    # Hero: nearest future if available, else first available
    hero = None
    for e in events:
        if e.start and e.start >= now:
            hero = e
            break
    if not hero and events:
        hero = events[0]

    # If you specifically want a single TicketType for hero,
    # e.g., the first by sales_start:
    next_show = hero  # keep your naming if you need it elsewhere
    next_tt = None
    next_sales_end = None
    if next_show:
        # Use the prefetched list (no DB hit), or fall back to manager
        types_list = getattr(next_show, "prefetched_types", None) or list(next_show.ticket_types.all())
        if types_list:
            next_tt = types_list[0]  # because we ordered in Prefetch
        # Or aggregate to get the earliest sales_end:
        next_sales_end = next_show.first_sales_end  # annotated above

    # Distinct filter options from Venues that have published events
    vqs = Venue.objects.filter(event__published=True)
    cities = (vqs.exclude(city="").exclude(city__isnull=True)
                  .values_list("city", flat=True).distinct().order_by("city"))
    states = (vqs.exclude(state="").exclude(state__isnull=True)
                  .values_list("state", flat=True).distinct().order_by("state"))
    venues = (vqs.exclude(name="").exclude(name__isnull=True)
                  .values_list("name", flat=True).distinct().order_by("name"))

    ctx = {
        "hero": hero,
        "events": events,
        "filters": {"city": city, "state": state, "venue": venue, "past": "1" if show_past else ""},
        "cities": cities,
        "states": states,
        "venues": venues,
        "next_show": next_show,
        "next_tt": next_tt,                  # a single TicketType (or None)
        "next_sales_end": next_sales_end,    # a datetime (or None)
        "now": now,
    }
    return render(request, "events/public_events.html", ctx)