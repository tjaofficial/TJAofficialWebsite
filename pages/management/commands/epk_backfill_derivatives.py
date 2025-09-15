from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from pages.models import ArtistPhoto, Artist
from coreutils.images import generate_derivatives  # uses storage API (no .path)

class Command(BaseCommand):
    help = "Generate AVIF/WebP derivatives for ArtistPhoto images. Optionally include Artist avatar/hero."

    def add_arguments(self, parser):
        parser.add_argument(
            "--include-artist",
            action="store_true",
            help="Also generate derivatives for Artist.avatar and Artist.hero_image",
        )
        parser.add_argument(
            "--widths",
            type=str,
            default="",
            help="Comma-separated widths, e.g. 320,640,1024,1600 (defaults to settings.EPK_IMAGE_WIDTHS)",
        )

    def handle(self, *args, **opts):
        widths = None
        if opts["widths"]:
            try:
                widths = [int(x.strip()) for x in opts["widths"].split(",") if x.strip()]
            except Exception:
                self.stderr.write("Invalid --widths. Use e.g. 320,640,1024,1600")
                return

        # --- ArtistPhoto ---
        total = ArtistPhoto.objects.count()
        ok = err = 0
        self.stdout.write(f"Processing ArtistPhoto… total={total}")
        for i, p in enumerate(ArtistPhoto.objects.iterator(), 1):
            if not getattr(p, "image", None):
                self.stdout.write(f"[{i}/{total}] id={p.id} (no image) — skip")
                continue
            try:
                generate_derivatives(p.image, widths=widths)
                self.stdout.write(f"[{i}/{total}] {p.id} ok")
                ok += 1
            except Exception as e:
                self.stderr.write(f"[{i}/{total}] {p.id} error: {e}")
                err += 1

        self.stdout.write(f"ArtistPhoto done: ok={ok}, err={err}")

        # --- Artist (optional) ---
        if opts["include_artist"]:
            atotal = Artist.objects.count()
            aok = aerr = 0
            self.stdout.write(f"Processing Artist avatar/hero… total={atotal}")
            for j, a in enumerate(Artist.objects.iterator(), 1):
                for field in ("avatar", "hero_image"):
                    img = getattr(a, field, None)
                    if not img:
                        continue
                    try:
                        generate_derivatives(img, widths=widths)
                        self.stdout.write(f"[{j}/{atotal}] Artist {a.id} {field} ok")
                        aok += 1
                    except Exception as e:
                        self.stderr.write(f"[{j}/{atotal}] Artist {a.id} {field} error: {e}")
                        aerr += 1
            self.stdout.write(f"Artist images done: ok={aok}, err={aerr}")

        self.stdout.write("All done.")
