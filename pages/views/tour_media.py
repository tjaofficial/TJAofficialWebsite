from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from ..models import MediaAlbum

def tour_media(request):
    city = (request.GET.get("city") or "").strip()
    state = (request.GET.get("state") or "").strip().upper()
    year = (request.GET.get("year") or "").strip()

    albums = MediaAlbum.objects.filter(is_public=True)
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

    # list of distinct years for filter
    distinct_years = sorted({a.date.year for a in MediaAlbum.objects.filter(is_public=True, date__isnull=False)}, reverse=True)

    return render(request, "tour/media.html", {
        "year_groups": year_groups,
        "filters": {"city": city, "state": state, "year": year},
        "distinct_years": distinct_years,
    })

def tour_media_album(request, slug):
    album = get_object_or_404(MediaAlbum, slug=slug, is_public=True)
    return render(request, "tour/media_album.html", {"album": album})
