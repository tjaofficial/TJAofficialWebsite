from django.core.mail import send_mass_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from tickets.utils import qr_png_bytes
from django.utils import timezone

def enqueue_mass_email(subscribers, subject, body, from_email=None):
    messages = []
    for s in subscribers:
        messages.append((subject, body, from_email, [s.email]))
    send_mass_mail(messages, fail_silently=False)

def send_tickets_email(email, tickets, site_base=None):
    site_base = settings.SITE_BASE_URL
    subject = "Your Tickets"
    context = {"tickets": tickets, "site_base": site_base}
    html = render_to_string("tickets/email_tickets.html", context)

    msg = EmailMultiAlternatives(
        subject, 
        "Your tickets are attached.", 
        to=[email],
        bcc=["tjaofficialbooking@gmail.com"],
    )
    msg.attach_alternative(html, "text/html")

    # Attach one PNG per ticket
    for t in tickets:
        verify_url = f"{site_base}{reverse('control:tickets:ticket_detail', args=[t.qr_token])}"
        png = qr_png_bytes(verify_url)
        filename = f"ticket_{t.qr_token}.png"
        msg.attach(filename, png, "image/png")

    msg.send(fail_silently=False)


def send_notification_update(topic, extra, request=None):
    EMAIL_TOPICS = {
        "subscribers": {
            "template": "emails/new_subscribers.html",
            "subject": "New Subscribers!",
            "context": {
                "site_base": settings.SITE_BASE_URL,
                "now": timezone.now(),
                "subscriber": extra if topic == "subscribers" else ""
            }
        },
        "rewards": {
            "template": "emails/new_rewards.html",
            "subject": "New Rewards Subscribers!",
            "context": {
                "site_base": settings.SITE_BASE_URL,
                "now": timezone.now(),
                "rewards": extra if topic == "rewards" else ""
            }
        },
        "order": {
            "template": "emails/new_order.html",
            "subject": "New Order(s)!",
            "context": {
                "site_base": settings.SITE_BASE_URL,
                "now": timezone.now(),
                "order": extra if topic == "order" else ""
            }
        },
        "tickets": {
            "template": "emails/new_tickets.html",
            "subject": "More Tickets Bought!",
            "context": {
                "site_base": settings.SITE_BASE_URL,
                "now": timezone.now(),
                "tickets": extra if topic == "tickets" else ""
            }
        }
    }
    to_email = [settings.DEFAULT_FROM_EMAIL]


    # Render HTML; make a text fallback automatically if no .txt template exists
    html_body = render_to_string(EMAIL_TOPICS[topic]['template'], EMAIL_TOPICS[topic]['context'])

    msg = EmailMultiAlternatives(
        subject=EMAIL_TOPICS[topic]['subject'],
        to=to_email
    )
    msg.attach_alternative(html_body, "text/html")

    return msg.send(fail_silently=False)