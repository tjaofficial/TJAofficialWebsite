from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from ..models import Show
from ..forms import ShowForm
from collections import defaultdict
from django.utils.timezone import make_aware
from django.contrib import messages
from django.utils.timezone import now, localtime

def shows(request):
    qs = Show.objects.all().order_by("date")
    # Next upcoming (>= now)
    _now = now()
    next_show = qs.filter(date__gte=_now).first()

    # Group by "Month YYYY"
    grouped = defaultdict(list)
    for s in qs:
        label = localtime(s.date).strftime("%B %Y")
        grouped[label].append(s)
    shows_by_month = sorted(grouped.items(), key=lambda x: x[0])

    return render(request, "pages/shows.html", {
        "shows_by_month": shows_by_month,
        "next_show": next_show,
    })

@login_required(login_url="/admin/login/")
def add_show(request):
    if request.method == "POST":
        form = ShowForm(request.POST)
        if form.is_valid():
            show = form.save(commit=False)
            # If your project uses timezone-aware datetimes, ensure awareness:
            if show.date.tzinfo is None:
                show.date = make_aware(show.date)
            show.save()
            messages.success(request, "Show added ✅")
            return redirect("shows")  # your existing shows URL name
    else:
        form = ShowForm()

    return render(request, "pages/show_form.html", {"form": form})