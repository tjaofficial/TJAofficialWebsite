from django.shortcuts import render
from django.utils import timezone
from ..models import Show, Video, Release
from shop.models import Product
from django.conf import settings

def home(request):
    # Pull a few highlights; each block is optional — template guards for empty lists.
    products = Product.objects.filter(is_active=True).order_by("-created_at")[:4]
    shows = Show.objects.filter(date__gte=timezone.now()).order_by("date")[:4]
    videos = Video.objects.filter(is_public=True).order_by("-published_at")[:3]
    releases = Release.objects.filter(is_public=True).order_by("-release_date")[:3] if "pages" in settings.INSTALLED_APPS else []
    return render(request, "pages/home.html", {
        "products": products,
        "shows": shows,
        "videos": videos,
        "releases": releases,
    })
