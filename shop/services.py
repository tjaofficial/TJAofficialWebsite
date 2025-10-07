# shop/services.py
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.utils import timezone


def send_order_shipped_email(order, request=None):
    """
    Sends a shipping confirmation to the buyer, BCC to DEFAULT_FROM_EMAIL.
    Looks for templates:
      templates/shop/email_shipped.html
      templates/shop/email_shipped.txt  (optional plain-text)
    """
    # Who it's from + who it goes to
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [order.email] if getattr(order, "email", None) else []
    if not to_email:
        return 0  # nothing to send

    bcc = [from_email]  # your copy, hidden from recipient

    # Context for templates
    ctx = {
        "order": order,
        "site_base": settings.SITE_BASE_URL,
        "support_email": getattr(settings, "SHOP_SUPPORT_EMAIL", from_email),
        "brand": getattr(settings, "SHOP_BRAND_NAME", "TJAofficial"),
        "now": timezone.now(),
    }

    subject = f"Your {ctx['brand']} order #{order.number or order.pk} has shipped!"

    # Render HTML; make a text fallback automatically if no .txt template exists
    html_body = render_to_string("shop/email_shipped.html", ctx)
    try:
        text_body = render_to_string("shop/email_shipped.txt", ctx)
    except Exception:
        text_body = strip_tags(html_body)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=to_email,
        bcc=bcc,
    )
    msg.attach_alternative(html_body, "text/html")
    return msg.send(fail_silently=False)
