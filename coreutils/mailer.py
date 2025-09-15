from django.core.mail import send_mass_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from tickets.utils import qr_png_bytes

def enqueue_mass_email(subscribers, subject, body, from_email=None):
    messages = []
    for s in subscribers:
        messages.append((subject, body, from_email, [s.email]))
    send_mass_mail(messages, fail_silently=False)

def send_tickets_email(email, tickets, site_base=None):
    site_base = site_base or getattr(settings, "SITE_BASE_URL", "http://127.0.0.1:8000")
    subject = "Your Tickets"
    context = {"tickets": tickets, "site_base": site_base}
    html = render_to_string("tickets/email_tickets.html", context)

    msg = EmailMultiAlternatives(subject, "Your tickets are attached.", to=[email])
    msg.attach_alternative(html, "text/html")

    # Attach one PNG per ticket
    for t in tickets:
        verify_url = f"{site_base}{reverse('control:tickets:ticket_detail', args=[t.qr_token])}"
        png = qr_png_bytes(verify_url)
        filename = f"ticket_{t.qr_token}.png"
        msg.attach(filename, png, "image/png")

    msg.send(fail_silently=False)