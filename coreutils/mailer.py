from django.core.mail import send_mass_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from tickets.utils import qr_png_bytes
from django.utils import timezone
import qrcode
from io import BytesIO
from email.mime.image import MIMEImage

def enqueue_mass_email(subscribers, subject, body, from_email=None):
    messages = []
    for s in subscribers:
        messages.append((subject, body, from_email, [s.email]))
    send_mass_mail(messages, fail_silently=False)

def qr_png_bytes(data: str) -> bytes:
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def send_tickets_email(email, tickets, site_base=None):
    site_base = settings.SITE_BASE_URL
    subject = "Your Tickets"

    # Prepare inline images (cid + bytes)
    inline_imgs = []
    for t in tickets:
        cid = f"qr_{t.qr_token}"  # referenced as src="cid:qr_..."
        verify_url = f"{site_base}{reverse('control:tickets:ticket_detail', args=[t.qr_token])}"
        png = qr_png_bytes(verify_url)
        inline_imgs.append({"ticket": t, "cid": cid, "png": png})

    # Render HTML that uses the cid values
    context = {"inline_imgs": inline_imgs, "site_base": site_base}
    html = render_to_string("tickets/email_tickets.html", context)

    # Make HTML the main body; mark message as multipart/related
    msg = EmailMultiAlternatives(
        subject=subject,
        body=html,                           # HTML as body
        to=[email],
        bcc=["tjaofficialbooking@gmail.com"],
    )
    msg.content_subtype = "html"            # text/html
    msg.mixed_subtype = "related"           # so inline images bind to this HTML

    # Attach inline images with Content-ID headers
    for item in inline_imgs:
        img = MIMEImage(item["png"])
        img.add_header("Content-ID", f"<{item['cid']}>")  # angle brackets required
        img.add_header("Content-Disposition", "inline",
                      filename=f"ticket_{item['ticket'].qr_token}.png")
        msg.attach(img)

        # Optional: also attach a downloadable copy
        # msg.attach(f"ticket_{item['ticket'].qr_token}.png", item["png"], "image/png")

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