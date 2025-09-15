from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from bookingstack.models import SocialMetricSnapshot
from bookingstack.utils_geo import normalize_city
from datetime import datetime

# NOTE: Implement real API calls later; these are safe stubs you can run today.

def fetch_spotify_city_monthlies(artist_spotify_id: str, city: str, radius_km: int) -> int:
    # TODO: implement via Spotify + a geo mapping of listeners (requires partners or estimates).
    # For now return a deterministic pseudo-number so UI works.
    base = sum(ord(c) for c in city) % 700
    return 800 + base

def fetch_instagram_local_followers(ig_handle: str, city: str, radius_km: int) -> int:
    # TODO: IG Graph API with location insights or your own estimator (hashtags/geo tags).
    base = sum(ord(c) for c in city) % 500
    return 1200 + base

def fetch_tiktok_local_followers(tt_handle: str, city: str, radius_km: int) -> int:
    # TODO: TikTok Business API / estimates.
    base = sum(ord(c) for c in city) % 400
    return 900 + base

class Command(BaseCommand):
    help = "Refresh SocialMetricSnapshot for a given city (or multiple)."

    def add_arguments(self, parser):
        parser.add_argument("--city", type=str, help="Target city (e.g., Detroit). If omitted, uses a default list.")
        parser.add_argument("--radius", type=int, default=80, help="Metro radius in km (default 80).")
        parser.add_argument("--spotify_id", type=str, default="", help="Artist Spotify ID (optional for real fetch).")
        parser.add_argument("--ig_handle", type=str, default="tjaofficial", help="IG handle (default tjaofficial).")
        parser.add_argument("--tiktok_handle", type=str, default="tjaofficial", help="TikTok handle (default tjaofficial).")

    def handle(self, *args, **opts):
        cities = [opts["city"]] if opts["city"] else ["Detroit", "Chicago", "Cleveland"]
        radius = int(opts["radius"])
        spotify_id = opts["spotify_id"] or ""
        ig = opts["ig_handle"]
        tt = opts["tiktok_handle"]

        created = 0
        for city in cities:
            c = normalize_city(city)
            sm = SocialMetricSnapshot.objects.create(
                city=c,
                metro_radius_km=radius,
                spotify_monthly_listeners=fetch_spotify_city_monthlies(spotify_id, c, radius),
                instagram_local_followers=fetch_instagram_local_followers(ig, c, radius),
                tiktok_local_followers=fetch_tiktok_local_followers(tt, c, radius),
            )
            created += 1
            self.stdout.write(self.style.SUCCESS(f"Saved SocialMetricSnapshot for {c} at {sm.created_at}"))
        self.stdout.write(self.style.SUCCESS(f"Done. {created} snapshots created."))
