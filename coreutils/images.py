# coreutils/images.py
import os
from io import BytesIO
from PIL import Image
from django.conf import settings
from django.core.files.base import ContentFile

def _ext(path): return os.path.splitext(path)[1].lower()

def generate_derivatives(dj_file, widths=None):
    """
    Given a Django File/ImageField file, generate resized AVIF+WebP
    next to the original. Returns dict: {"avif": [(w, path), ...], "webp": [...]}.
    """
    widths = widths or getattr(settings, "EPK_IMAGE_WIDTHS", [320, 640, 1024, 1600])
    if not dj_file: return {"avif": [], "webp": []}

    orig_path = dj_file.path
    base_dir  = os.path.dirname(orig_path)
    base_name = os.path.splitext(os.path.basename(orig_path))[0]

    out = {"avif": [], "webp": []}

    with Image.open(orig_path) as im:
        im.load()
        # Convert to RGB for consistent saving
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        w0, h0 = im.size

        for w in widths:
            if w >= w0:
                # No need to upscale; cap at original
                w = w0
            h = int(h0 * (w / w0))
            im_resized = im.copy()
            im_resized.thumbnail((w, h), Image.LANCZOS)

            # AVIF
            avif_name = f"{base_name}_w{w}.avif"
            avif_path = os.path.join(base_dir, avif_name)
            if not os.path.exists(avif_path):
                buf = BytesIO()
                im_resized.save(buf, format="AVIF", quality=getattr(settings, "EPK_AVIF_QUALITY", 45))
                with open(avif_path, "wb") as f:
                    f.write(buf.getvalue())
            out["avif"].append((w, dj_file.storage.url(os.path.join(os.path.dirname(dj_file.name), avif_name))))

            # WebP
            webp_name = f"{base_name}_w{w}.webp"
            webp_path = os.path.join(base_dir, webp_name)
            if not os.path.exists(webp_path):
                buf = BytesIO()
                im_resized.save(buf, format="WEBP", quality=getattr(settings, "EPK_WEBP_QUALITY", 82), method=6)
                with open(webp_path, "wb") as f:
                    f.write(buf.getvalue())
            out["webp"].append((w, dj_file.storage.url(os.path.join(os.path.dirname(dj_file.name), webp_name))))

    # dedupe in case of non-upscaled duplicates
    out["avif"] = sorted(set(out["avif"]))
    out["webp"] = sorted(set(out["webp"]))
    return out
