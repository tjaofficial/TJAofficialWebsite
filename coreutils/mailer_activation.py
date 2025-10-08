# coreutils/mailer_activation.py
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

def send_activation_email(user, request=None):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    path = reverse("rewards:activate", args=[uid, token])
    if request is not None:
        activate_url = request.build_absolute_uri(path)
    else:
        base = getattr(settings, "SITE_BASE_URL", "").rstrip("/")
        activate_url = f"{base}{path}"

    ctx = {
        "user": user,
        "activate_url": activate_url,
        "site_base": getattr(settings, "SITE_BASE_URL", ""),
    }

    subject = "Confirm your TJA Rewards account"
    html_body = render_to_string("emails/activation_email.html", ctx)

    msg = EmailMultiAlternatives(
        subject=subject,
        to=[user.email],
        # optional: bcc to ops mailbox so you see activations (user won't see)
        bcc=[getattr(settings, "DEFAULT_FROM_EMAIL", "")] if getattr(settings, "DEFAULT_FROM_EMAIL", "") else None,
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)
