from django.shortcuts import render
from django.utils import timezone
from ..models import Video, Release
from events.models import Event
from tickets.models import TicketType
from shop.models import Product
from django.conf import settings
from django.db.models import Prefetch, Exists, Min, OuterRef

def home(request):
    # Pull a few highlights; each block is optional — template guards for empty lists.
    products = Product.objects.filter(is_active=True).order_by("-created_at")[:4]

    active_types = TicketType.objects.filter(active=True, name="General Admission").order_by('price_cents', 'sales_start')
    shows = (
        Event.objects
        .filter(published=True, start__date__gte=timezone.now())
        .select_related("venue")
        .prefetch_related(Prefetch("ticket_types", queryset=active_types, to_attr="prefetched_types"))
        .annotate(
            has_tickets=Exists(
                TicketType.objects.filter(event_id=OuterRef("pk"), active=True)
            ),
            # Example: the earliest sales_end across all TTs for this event
            first_sales_end=Min("ticket_types__sales_end")
        )
        .order_by("start")[:4]
    )
    videos = Video.objects.filter(is_public=True).order_by("-published_at")[:3]
    releases = Release.objects.filter(is_public=True).order_by("-release_date")[:4] if "pages" in settings.INSTALLED_APPS else []
    return render(request, "pages/home.html", {
        "products": products,
        "shows": shows,
        "videos": videos,
        "releases": releases,
    })
