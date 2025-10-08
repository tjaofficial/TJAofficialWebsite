from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import TicketType, Ticket, TicketReservation
from events.models import Event, ArtistSaleLink
from .forms import TicketTypeForm
from django.http import HttpResponse, JsonResponse
from django.utils.http import urlencode
from django.views.decorators.http import require_POST
from django.db import transaction
import qrcode
from io import BytesIO
import re
from uuid import UUID
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from coreutils.mailer import send_tickets_email
import stripe, json
from django.utils import timezone
from django.db.models import Q, Sum, Count
import csv
from django.contrib import messages
from django.urls import reverse
from datetime import timedelta
import logging
from coreutils.mailer import send_notification_update

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY
is_super = user_passes_test(lambda u: u.is_superuser)

@is_super
def tickettypes_list(request):
    qs = TicketType.objects.select_related("event").order_by("-event__start", "name")
    return render(request, "tickets/list.html", {"types": qs})

@is_super
def tickettype_add(request):
    form = TicketTypeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("control:tickets:list")
    return render(request, "tickets/form.html", {"form": form, "mode": "add"})

@is_super
def tickettype_edit(request, pk):
    tt = get_object_or_404(TicketType, pk=pk)
    form = TicketTypeForm(request.POST or None, instance=tt)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("control:tickets:list")
    return render(request, "tickets/form.html", {"form": form, "mode": "edit", "tt": tt})

# --- QR PNG endpoint ---
@is_super
def qr_png(request, token):
    verify_url = request.build_absolute_uri(
        f"/control/tickets/ticket/{token}/"
    )
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type="image/png")

# --- Scanner page ---
@is_super
def scan_page(request):
    return render(request, "tickets/scan.html")

@require_POST
@is_super
def scan_check(request):
    raw = request.POST.get("code", "").strip()
    token = _extract_token(raw)
    if not token:
        return render(request, "tickets/scan.html", {"error": "Invalid input."})

    t = Ticket.objects.filter(qr_token=token).select_related("ticket_type","ticket_type__event").first()
    return render(request, "tickets/scan.html", {"ticket": t})

def _extract_token(text: str):
    m = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", text, re.I)
    if m:
        try:
            return UUID(m.group(0))
        except Exception:
            return None
    return None

# --- Ticket detail ---
@is_super
def ticket_detail(request, token):
    t = get_object_or_404(Ticket.objects.select_related("ticket_type","ticket_type__event"), qr_token=token)
    return render(request, "tickets/ticket_detail.html", {"t": t})

# --- Ticket check-in ---
@require_POST
@is_super
def ticket_checkin(request, token):
    t = get_object_or_404(Ticket, qr_token=token)
    if not t.is_checked_in():
        t.check_in()
    return redirect("control:tickets:ticket_detail", token=t.qr_token)

# --- Bulk issue helper ---
@is_super
def issue_tickets(request):
    if request.method == "POST":
        tt_id = request.POST.get("ticket_type")
        qty = int(request.POST.get("qty") or 0)
        tt = get_object_or_404(TicketType, id=tt_id)
        created = []
        with transaction.atomic():
            for _ in range(qty):
                created.append(Ticket.objects.create(ticket_type=tt))
        return render(request, "tickets/issue_done.html", {"created": created, "tt": tt})
    else:
        types = TicketType.objects.select_related("event").order_by("-event__start", "name")
        return render(request, "tickets/issue_form.html", {"types": types})
    
@csrf_exempt
def stripe_webhook(request):
    GRACE = timedelta(minutes=5)

    holds = (TicketReservation.objects
            .select_for_update()
            .filter(
                id__in=ids,
                stripe_session_id=session_id,
                fulfilled=False,
                expires_at__gt=timezone.now() - GRACE  # <-- allow slight lateness
            ))
    payload = request.body
    sig = request.META.get("HTTP_STRIPE_SIGNATURE")
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session.get("id")
        email = (session.get("customer_details") or {}).get("email") or session.get("metadata", {}).get("purchaser_email", "")
        name  = (session.get("customer_details") or {}).get("name") or session.get("metadata", {}).get("purchaser_name", "")
        artist_id_meta = (session.get("metadata") or {}).get("sold_by_artist_id")
        reservation_ids = (session.get("metadata") or {}).get("reservation_ids", "")
        ids = [int(x) for x in reservation_ids.split(",") if x.strip().isdigit()]

        # fulfill under transaction; ignore if already done (idempotent)
        from django.db import transaction
        with transaction.atomic():
            holds = (TicketReservation.objects
                     .select_for_update()
                     .filter(id__in=ids, stripe_session_id=session_id, fulfilled=False, expires_at__gt=timezone.now()))
            if not holds:
                return HttpResponse(status=200)
            tickets_created = []
            for h in holds:
                # issue h.qty tickets
                for _ in range(h.qty):
                    t = Ticket.objects.create(
                        ticket_type=h.ticket_type,
                        purchaser_email=email,
                        purchaser_name=name or h.purchaser_name,
                        sold_by_artist_id = int(artist_id_meta) if artist_id_meta else None,
                        payment_method = "card"
                    )
                    tickets_created.append(t)
                h.fulfilled = True
                h.save(update_fields=["fulfilled"])

        # email the QR links (or images)
        if tickets_created and email:
            try:
                send_tickets_email(email, tickets_created, site_base=settings.SITE_BASE_URL)
                send_notification_update('tickets', tickets_created, request=request)
            except Exception as e:
                logger.exception("Ticket email send failed for session %s to %s", session_id, email)


    return HttpResponse(status=200)

@login_required
def scan_foh(request):
    """
    Front-of-house continuous scanner UI.
    ?autocheckin=1 will auto-check in on successful scan.
    """
    autocheck = request.GET.get("autocheckin") in ("1", "true", "yes")
    return render(request, "tickets/scan_foh.html", {"autocheck": autocheck})

def _extract_uuid(text: str):
    m = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", text, re.I)
    if not m:
        return None
    try:
        return UUID(m.group(0))
    except Exception:
        return None

@csrf_exempt  # we’re posting from JS; you can add CSRF if you prefer
@is_super
def scan_api(request):
    """
    POST JSON: {"code": "...", "autocheckin": true/false}
    Returns JSON with status: "ok" | "already" | "invalid"
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    raw = (data.get("code") or "").strip()
    token = _extract_uuid(raw)
    if not token:
        return JsonResponse({"status": "invalid", "message": "No valid token found."})

    t = Ticket.objects.select_related("ticket_type", "ticket_type__event").filter(qr_token=token).first()
    if not t:
        return JsonResponse({"status": "invalid", "message": "Ticket not found."})

    # If autocheckin requested, mark as checked in (idempotent)
    autocheck = bool(data.get("autocheckin"))
    if t.checked_in_at:
        return JsonResponse({
            "status": "already",
            "message": "Already checked in.",
            "ticket": {
                "event": t.ticket_type.event.name if t.ticket_type and t.ticket_type.event else "",
                "type": t.ticket_type.name if t.ticket_type else "",
                "email": t.purchaser_email,
                "name": t.purchaser_name,
                "checked_in_at": t.checked_in_at.isoformat(),
                "token": str(t.qr_token),
            }
        })

    if autocheck:
        t.checked_in_at = timezone.now()
        t.save(update_fields=["checked_in_at"])

    return JsonResponse({
        "status": "ok",
        "message": "Valid ticket.",
        "ticket": {
            "event": t.ticket_type.event.name if t.ticket_type and t.ticket_type.event else "",
            "type": t.ticket_type.name if t.ticket_type else "",
            "email": t.purchaser_email,
            "checked_in_at": t.checked_in_at.isoformat() if t.checked_in_at else None,
            "token": str(t.qr_token),
        }
    })

@is_super
def tickets_sold(request):
    qs = (Ticket.objects
          .select_related("ticket_type", "ticket_type__event")
          .order_by("-issued_at"))

    event_id = request.GET.get("event") or ""
    date_from = request.GET.get("from") or ""
    date_to   = request.GET.get("to") or ""
    name_q    = request.GET.get("name") or ""
    email_q   = request.GET.get("email") or ""
    checked   = request.GET.get("checked") or ""  # "yes" | "no" | ""

    if event_id:
        qs = qs.filter(ticket_type__event_id=event_id)
    if date_from:
        qs = qs.filter(issued_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(issued_at__date__lte=date_to)
    if name_q:
        qs = qs.filter(purchaser_name__icontains=name_q)
    if email_q:
        qs = qs.filter(purchaser_email__icontains=email_q)
    if checked == "yes":
        qs = qs.filter(checked_in_at__isnull=False)
    elif checked == "no":
        qs = qs.filter(checked_in_at__isnull=True)

    # summary
    total = qs.count()
    checked_in = qs.filter(checked_in_at__isnull=False).count()

    # per-event totals (sold / remaining / checkins), honoring the same event filter
    ev_base = Event.objects.all()
    if event_id:
        ev_base = ev_base.filter(id=event_id)

    # pull quantities and realized tickets for each event
    ev_qs = (ev_base
             .annotate(total_capacity=Sum("ticket_types__quantity"),
                       sold=Count("ticket_types__tickets"),
                       checked_in=Count("ticket_types__tickets",
                                        filter=Q(ticket_types__tickets__checked_in_at__isnull=False)))
             .order_by("-start"))

    events_summary = []
    for ev in ev_qs:
        cap = ev.total_capacity or 0
        sold = ev.sold or 0
        remaining = max(0, cap - sold)
        events_summary.append({
            "id": ev.id,
            "name": ev.name or "(unnamed)",
            "date": ev.start,
            "capacity": cap,
            "sold": sold,
            "remaining": remaining,
            "checked_in": ev.checked_in or 0,
        })

    events = Event.objects.order_by("-start")

    ctx = {
        "tickets": qs[:1000],
        "events": events,
        "q": {"event": event_id, "from": date_from, "to": date_to,
              "name": name_q, "email": email_q, "checked": checked},
        "summary": {"total": total, "checked_in": checked_in},
        "events_summary": events_summary,   # <-- add
    }
    return render(request, "tickets/sales.html", ctx)

@is_super
def tickets_sold_export(request):
    qs = (Ticket.objects
          .select_related("ticket_type", "ticket_type__event")
          .order_by("-issued_at"))

    # same filters as above
    event_id = request.GET.get("event") or ""
    date_from = request.GET.get("from") or ""
    date_to   = request.GET.get("to") or ""
    name_q    = request.GET.get("name") or ""
    email_q   = request.GET.get("email") or ""
    checked   = request.GET.get("checked") or ""

    if event_id:
        qs = qs.filter(ticket_type__event_id=event_id)
    if date_from:
        qs = qs.filter(issued_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(issued_at__date__lte=date_to)
    if name_q:
        qs = qs.filter(purchaser_name__icontains=name_q)
    if email_q:
        qs = qs.filter(purchaser_email__icontains=email_q)
    if checked == "yes":
        qs = qs.filter(checked_in_at__isnull=False)
    elif checked == "no":
        qs = qs.filter(checked_in_at__isnull=True)

    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = "attachment; filename=tickets_sold.csv"
    w = csv.writer(resp)
    w.writerow(["issued_at","event","type","purchaser_name","purchaser_email","checked_in_at","qr_token","price_cents"])
    for t in qs.iterator():
        w.writerow([
            t.issued_at.strftime("%Y-%m-%d %H:%M"),
            getattr(getattr(t.ticket_type, "event", None), "name", ""),
            getattr(t.ticket_type, "name", ""),
            t.purchaser_name,
            t.purchaser_email,
            t.checked_in_at.strftime("%Y-%m-%d %H:%M") if t.checked_in_at else "",
            str(t.qr_token),
            getattr(t.ticket_type, "price_cents", 0),
        ])
    return resp

@require_POST
@is_super
def ticket_resend_email(request, token):
    t = get_object_or_404(Ticket.objects.select_related("ticket_type", "ticket_type__event"), qr_token=token)
    if not t.purchaser_email:
        messages.error(request, "No purchaser email on this ticket.")
        return redirect("control:tickets:ticket_detail", token=token)

    send_tickets_email(t.purchaser_email, [t])  # single-ticket resend with PNG attached
    messages.success(request, "Ticket email re-sent.")
    return redirect("control:tickets:ticket_detail", token=token)

def public_purchase(request, event_id):
    ev = get_object_or_404(Event, pk=event_id, published=True)  # or your flag
    types = TicketType.objects.filter(event=ev, active=True).order_by("price_cents")

    # Compute derived attributes for template usage
    for tt in types:
        tt.remaining = tt.remaining()          # int
        tt.is_on_sale = tt.is_on_sale()           # bool
    
    artist_token = request.GET.get("artist")  # may be None

    # Build login URL with ?next back to this page + preserve artist token
    next_qs = {"next": request.get_full_path()}
    login_url = settings.LOGIN_URL if hasattr(settings, "LOGIN_URL") else reverse("control:accounts:login")
    if "://" not in login_url:
        # make it absolute for some auth setups
        login_url = settings.SITE_BASE_URL + login_url
    login_href = f"{login_url}?{urlencode(next_qs)}"

    return render(request, "tickets/public_purchase.html", {
        "event": ev, 
        "types": types, 
        "artist_token": artist_token,
        "login_href": login_href,
    })

def public_create_checkout(request, event_id):
    if request.method != "POST":
        return redirect("control:tickets:public_purchase", event_id=event_id)

    ev = get_object_or_404(Event, pk=event_id, published=True)

    if request.user.is_authenticated:
        purchaser_email = (request.user.email or "").strip()
        purchaser_name  = (f"{getattr(request.user, 'first_name', '')} {getattr(request.user, 'last_name', '')}".strip()
                           or getattr(request.user, 'username', ''))
    else:
        purchaser_email = (request.POST.get("email") or "").strip()
        purchaser_name  = (request.POST.get("purchaser_name") or "").strip()

    artist_token = request.POST.get("artist_token") or request.GET.get("artist")
    artist_id = None
    if artist_token:
        link = (ArtistSaleLink.objects
                .filter(event=ev, token=artist_token, enabled=True)
                .select_related("artist").first())
        if link:
            artist_id = link.artist_id

    # Build selections (TicketType + qty)
    types = TicketType.objects.filter(event=ev, active=True)
    selections = []
    for tt in types:
        qty = int(request.POST.get(f"qty_{tt.id}", 0) or 0)
        if qty > 0:
            selections.append({"tt": tt, "qty": qty})

    if not selections:
        messages.error(request, "Select at least one ticket.")
        return redirect(f"{reverse('control:tickets:public_purchase', args=[ev.id])}?artist={artist_token or ''}")

    # Create holds (these should lock inventory)
    holds = TicketReservation.create_reservations(
        selections, 
        purchaser_email=purchaser_email, 
        purchaser_name=purchaser_name
    )

    # Build Stripe line items (use cents, Stripe expects integers)
    line_items = []
    for sel in selections:
        tt = sel["tt"]
        qty = sel["qty"]
        line_items.append({
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"{ev.name} — {tt.name}"},
                "unit_amount": tt.price_cents,  # in cents
            },
            "quantity": qty,
        })

    # Metadata for webhook fulfillment
    metadata = {
        "reservation_ids": ",".join(str(h.id) for h in holds),
        "event_id": str(ev.id),
        "purchaser_email": purchaser_email,
        "purchaser_name": purchaser_name,
    }
    if artist_id:
        metadata["sold_by_artist_id"] = str(artist_id)

    # URLs
    success_url = settings.SITE_BASE_URL + reverse("control:tickets:public_success", args=[ev.id]) + "?s={CHECKOUT_SESSION_ID}"
    cancel_url  = settings.SITE_BASE_URL + reverse("control:tickets:public_purchase", args=[ev.id])
    if artist_token:
        cancel_url += f"?artist={artist_token}"

    # Create session
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=line_items,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
        # optional niceties:
        # allow_promotion_codes=True,
        # billing_address_collection="auto",
    )

    # Persist session id & extend hold expiry a bit
    TicketReservation.objects.filter(id__in=[h.id for h in holds]).update(
        stripe_session_id=session.id,
        expires_at=timezone.now() + timedelta(minutes=30),
    )

    return redirect(session.url, permanent=False)

# tickets/views.py
def public_success(request, event_id):
    ev = get_object_or_404(Event, pk=event_id, published=True)
    # Webhook will actually fulfill & send email. This page is just a "thanks".
    return render(request, "tickets/public_success.html", {"event": ev})






