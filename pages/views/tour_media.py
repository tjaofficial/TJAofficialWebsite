from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count
from ..models import MediaAlbum
from ..forms import MediaSubmissionForm
from django.contrib import messages

def tour_media(request):
    city = (request.GET.get("city") or "").strip()
    state = (request.GET.get("state") or "").strip().upper()
    year = (request.GET.get("year") or "").strip()

    albums = (
        MediaAlbum.objects
        .filter(is_public=True)
        .select_related("cover_item")
        .annotate(item_count=Count("items"))
    )

    if city:
        albums = albums.filter(city__icontains=city)
    if state:
        albums = albums.filter(state__iexact=state)
    if year and year.isdigit():
        albums = albums.filter(date__year=int(year))

    # group by year, newest first
    years = {}
    for a in albums:
        y = a.date.year if a.date else 0
        years.setdefault(y, []).append(a)
    year_groups = sorted(years.items(), key=lambda t: t[0], reverse=True)

    distinct_years = sorted(
        {a.date.year for a in MediaAlbum.objects.filter(is_public=True, date__isnull=False)},
        reverse=True
    )

    return render(request, "tour/media.html", {
        "year_groups": year_groups,
        "filters": {"city": city, "state": state, "year": year},
        "distinct_years": distinct_years,
    })

def tour_media_submit(request):
    initial = {}
    album_slug = (request.GET.get("album") or "").strip()
    if album_slug:
        try:
            initial["album"] = MediaAlbum.objects.get(slug=album_slug, is_public=True)
        except MediaAlbum.DoesNotExist:
            pass

    if request.method == "POST":
        form = MediaSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Submitted! If approved, it will appear in that show’s album.")
            return redirect("tour_media_submit")
    else:
        form = MediaSubmissionForm(initial=initial)

    return render(request, "tour/media_submit.html", {"form": form})

def tour_media_album(request, slug):
    album = get_object_or_404(
        MediaAlbum.objects.select_related("cover_item").prefetch_related("items"),
        slug=slug, is_public=True
    )
    items = album.items.all()  # ordered by model Meta (sort, id)
    return render(request, "tour/media_album.html", {"album": album, "items": items})