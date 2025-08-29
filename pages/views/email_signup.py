from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone
from ..forms import EmailSignupForm
from ..models import Subscriber

def email_signup(request):
    just_subscribed = False

    if request.method == "POST":
        form = EmailSignupForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            name = form.cleaned_data.get("name","").strip()
            sub, created = Subscriber.objects.get_or_create(
                email=email,
                defaults={
                    "name": name,
                    "source": request.path,
                    "ip": request.META.get("REMOTE_ADDR"),
                    "user_agent": request.META.get("HTTP_USER_AGENT","")[:400],
                    "consent": True,
                },
            )
            if not created and name and not sub.name:
                sub.name = name
                sub.save(update_fields=["name"])

            just_subscribed = True
            # reset the form with new timestamp so bots can’t reuse it
            form = EmailSignupForm(initial={"ts": int(timezone.now().timestamp())})
        else:
            # keep form with errors; also refresh ts so a quick retry passes the time check
            form.fields["ts"].initial = int(timezone.now().timestamp())
    else:
        form = EmailSignupForm(initial={"ts": int(timezone.now().timestamp())})

    return render(request, "pages/email_signup.html", {
        "form": form,
        "just_subscribed": just_subscribed,
    })
