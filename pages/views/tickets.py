# tickets/views.py
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.http import Http404
from tickets.models import Ticket
from io import BytesIO
import base64, qrcode

def ticket_detail(request, token):
    t = (Ticket.objects
         .select_related("ticket_type", "ticket_type__event", "ticket_type__event__venue")
         .filter(qr_token=token)
         .first())
    if not t:
        raise Http404("Ticket not found")

    # Generate QR PNG as data: URI
    qr = qrcode.QRCode(box_size=8, border=2)
    # Use the same URL your scanners accept (or just the raw token).
    # Here we encode the token itself, which your FOH scanner already handles.
    qr.add_data(str(t.qr_token))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    qr_data_uri = "data:image/png;base64," + base64.b64encode(buf.read()).decode("ascii")

    ev = getattr(t.ticket_type, "event", None)
    venue = getattr(ev, "venue", None)

    ctx = {
        "t": t,
        "event": ev,
        "venue": venue,
        "qr_data_uri": qr_data_uri,
        "now": timezone.now(),
        # A canonical link people can share (this view’s URL that includes the token)
        "share_url": request.build_absolute_uri(),
    }
    return render(request, "tickets/public_ticket_detail.html", ctx)

# from tickets.models import TicketReservation, Ticket
# from coreutils.mailer import send_tickets_email
# from django.conf import settings

# SESSION_ID = "cs_live_a1ObMQnGcTDUdZPEfQjGJhCu427frVMsIuEvuqrf8XodAbja13GYL2Jq72"

# res = TicketReservation.objects.filter(stripe_session_id=SESSION_ID).first()
# buyer_email = ((res.purchaser_email or "").strip() if res else "")
# print("Buyer email:", buyer_email or "(none)")

# qs = (Ticket.objects.filter(purchaser_email__iexact=buyer_email)
#       .select_related("ticket_type","ticket_type__event")) if buyer_email else Ticket.objects.none()
# tickets = list(qs)
# print("Tickets found:", len(tickets))

# bool(tickets) and send_tickets_email(buyer_email, tickets, site_base=settings.SITE_BASE_URL)
# print(("No tickets to send","Done")[bool(tickets)])


