from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from .models import Subscriber, Tag
from .forms import SubscriberForm, BulkSendForm
from coreutils.mailer import enqueue_mass_email

is_super = user_passes_test(lambda u: u.is_superuser)

@is_super
def subscribers_list(request):
    q = request.GET.get("q", "").strip()
    qs = Subscriber.objects.all()
    if q:
        qs = qs.filter(
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(city__icontains=q) |
            Q(state__icontains=q)
        )
    return render(request, "subscribers/subscribers.html", {"subs": qs, "q": q})

@is_super
def subscriber_add(request):
    form = SubscriberForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("subscribers:list")
    return render(request, "subscribers/add.html", {"form": form})

@is_super
def subscriber_detail(request, pk):
    s = get_object_or_404(Subscriber, pk=pk)
    return render(request, "subscribers/detail.html", {"s": s})

@is_super
def bulk_send(request):
    if request.method == "POST":
        form = BulkSendForm(request.POST)
        if form.is_valid():
            q = Q()
            if form.cleaned_data["state"]:
                q &= Q(state__iexact=form.cleaned_data["state"])
            if form.cleaned_data["birthday_month"]:
                q &= Q(birthday__month=form.cleaned_data["birthday_month"])
            if form.cleaned_data["tags"]:
                q &= Q(tags__in=form.cleaned_data["tags"])
            recipients = Subscriber.objects.filter(q).distinct()
            enqueue_mass_email(
                recipients,
                subject=form.cleaned_data["subject"],
                body=form.cleaned_data["body"]
            )
            return render(request, "subscribers/send_done.html", {"count": recipients.count()})
    else:
        form = BulkSendForm()
    return render(request, "subscribers/send.html", {"form": form})
