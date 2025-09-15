# pages/management/commands/epk_backfill_derivatives.py
from django.core.management.base import BaseCommand
from pages.models import ArtistPhoto
from coreutils.images import generate_derivatives

class Command(BaseCommand):
    help = "Generate AVIF/WebP derivatives for existing ArtistPhoto images"

    def handle(self, *args, **opts):
        qs = ArtistPhoto.objects.exclude(image="")
        total = qs.count()
        for i, p in enumerate(qs.iterator(), 1):
            if p.image:
                try:
                    generate_derivatives(p.image)
                    self.stdout.write(f"[{i}/{total}] {p.id} ok")
                except Exception as e:
                    self.stderr.write(f"[{i}/{total}] {p.id} error: {e}")
