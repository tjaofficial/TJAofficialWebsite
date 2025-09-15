# coreutils/images.py
import os
from io import BytesIO
from PIL import Image
from django.conf import settings
from django.core.files.base import ContentFile

def _split_name(name: str):
    """Return (dir, base_without_ext, ext) for a storage-relative name."""
    d = os.path.dirname(name)
    base = os.path.basename(name)
    stem, ext = os.path.splitext(base)
    return d, stem, ext.lower()

def _urls_to_srcset(pairs):
    # pairs is list[(width:int, url:str)]
    # produce "url1 320w, url2 640w, ..."
    return ", ".join([f"{u} {w}w" for (w, u) in pairs])

def generate_derivatives(dj_file, widths=None):
    """
    Storage-agnostic generator of AVIF/WebP derivatives.
    Returns dict:
      {
        "avif": [(w, url), ...],     # may be []
        "webp": [(w, url), ...],
      }
    """
    if not dj_file:
        return {"avif": [], "webp": []}

    widths = widths or getattr(settings, "EPK_IMAGE_WIDTHS", [320, 640, 1024, 1600])
    storage = dj_file.storage
    name = dj_file.name  # storage-relative path, e.g. "artists/photos/abc.jpg"

    dir_rel, stem, _ext = _split_name(name)

    # Load original via storage API (works for S3, GCS, filesystem, etc.)
    with storage.open(name, "rb") as f:
        buf = BytesIO(f.read())
    im = Image.open(buf)
    im.load()
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")

    w0, h0 = im.size
    avif_out, webp_out = [], []

    for w in widths:
        if w >= w0:  # don't upscale
            w2 = w0
        else:
            w2 = w
        h2 = int(h0 * (w2 / w0))

        im_resized = im.copy()
        im_resized.thumbnail((w2, h2), Image.LANCZOS)

        # Build storage-relative names
        avif_name = os.path.join(dir_rel, f"{stem}_w{w2}.avif")
        webp_name = os.path.join(dir_rel, f"{stem}_w{w2}.webp")

        # Save WebP
        if not storage.exists(webp_name):
            webp_q = getattr(settings, "EPK_WEBP_QUALITY", 82)
            out = BytesIO()
            im_resized.save(out, format="WEBP", quality=webp_q, method=6)
            storage.save(webp_name, ContentFile(out.getvalue()))
        webp_out.append((w2, storage.url(webp_name)))

    # De-dup & sort by width
    avif_out = sorted(set(avif_out))
    webp_out = sorted(set(webp_out))

    return {"avif": avif_out, "webp": webp_out}

def sources_for(dj_file, widths=None, check_exists=True):
    """
    Build srcset lists for existing derivatives only. Does NOT generate files.
    Safe for S3/GCS/local. Returns {
      "avif": "url 320w, url 640w, ...",
      "webp": "url 320w, ...",
      "fallback": original_url
    }
    """
    if not dj_file:
        return {"avif": "", "webp": "", "fallback": ""}

    widths = widths or getattr(settings, "EPK_IMAGE_WIDTHS", [320, 640, 1024, 1600])
    storage = dj_file.storage
    name = dj_file.name  # storage-relative (e.g., "artists/photos/abc.jpg")
    dir_rel, stem, _ext = _split_name(name)

    avif_pairs, webp_pairs = [], []
    for w in widths:
        avif_name = os.path.join(dir_rel, f"{stem}_w{w}.avif")
        webp_name = os.path.join(dir_rel, f"{stem}_w{w}.webp")
        # Only include files that exist (skip network checks if you prefer)
        if not check_exists or storage.exists(avif_name):
            avif_pairs.append((w, storage.url(avif_name)))
        if not check_exists or storage.exists(webp_name):
            webp_pairs.append((w, storage.url(webp_name)))

    def _pairs_to_srcset(pairs):
        return ", ".join([f"{u} {w}w" for (w, u) in pairs])

    return {
        "avif": _pairs_to_srcset(sorted(avif_pairs)),
        "webp": _pairs_to_srcset(sorted(webp_pairs)),
        "fallback": dj_file.url,
    }