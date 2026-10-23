from __future__ import annotations

import hashlib
import warnings as py_warnings
from io import BytesIO
from urllib.parse import urlsplit

from PIL import Image

from knowledge_engine.errors import LimitExceededError
from knowledge_engine.limits import Limits
from knowledge_engine.model import Asset


EXTENSION_BY_TYPE = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/svg+xml": "svg",
    "image/bmp": "bmp",
    "image/tiff": "tiff",
    "image/x-emf": "emf",
    "image/x-wmf": "wmf",
    "image/emf": "emf",
    "image/wmf": "wmf",
}
TYPE_BY_EXTENSION = {
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "jpe": "image/jpeg", "gif": "image/gif",
    "webp": "image/webp", "svg": "image/svg+xml", "bmp": "image/bmp", "tif": "image/tiff", "tiff": "image/tiff",
    "emf": "image/x-emf", "wmf": "image/x-wmf",
}
# Formats browsers cannot show are re-encoded to PNG when Pillow can decode them.
TRANSCODE_TO_PNG = {"image/tiff"}
SMALL_IMAGE = (180, 100)
SAFE_LINK_SCHEMES = {"http", "https", "mailto"}


def safe_href(target: str | None) -> str | None:
    """Return the link if it uses an allowed scheme, otherwise None."""
    if not target:
        return None
    target = target.strip()
    if target.startswith("#"):
        return target if len(target) > 1 else None
    try:
        scheme = urlsplit(target).scheme.lower()
    except ValueError:
        return None
    return target if scheme in SAFE_LINK_SCHEMES else None


class WarningLog:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.items: list[str] = []
        self._seen: set[str] = set()
        self.suppressed = 0

    def add(self, message: str) -> None:
        if message in self._seen:
            return
        if len(self.items) >= self.limit:
            self.suppressed += 1
            return
        self._seen.add(message)
        self.items.append(message)

    def finish(self) -> list[str]:
        if self.suppressed:
            return [*self.items, f"{self.suppressed} additional warnings were not listed."]
        return list(self.items)


def _probe(blob: bytes, max_pixels: int) -> tuple[int | None, int | None, Image.Image | None]:
    try:
        with py_warnings.catch_warnings():
            py_warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(BytesIO(blob))
            width, height = image.size
            if width * height > max_pixels:
                return width, height, None
            return width, height, image
    except Exception:
        return None, None, None


class AssetRegistry:
    """Collects images, de-duplicating identical bytes and naming files safely."""

    def __init__(self, source_kind: str, limits: Limits, warnings: WarningLog) -> None:
        self.source_kind = source_kind
        self.limits = limits
        self.warnings = warnings
        self.assets: list[Asset] = []
        self._by_hash: dict[str, Asset] = {}

    def add(
        self,
        blob: bytes,
        *,
        content_type: str | None,
        extension_hint: str | None,
        stem: str,
        position: int,
        alt: str | None,
        nearest_heading: str | None = None,
        nearest_step: str | None = None,
        slide: int | None = None,
        relationship_id: str | None = None,
    ) -> Asset:
        digest = hashlib.sha256(blob).hexdigest()
        existing = self._by_hash.get(digest)
        if existing:
            existing.occurrences += 1
            return existing
        if len(self.assets) >= self.limits.max_assets:
            raise LimitExceededError("too_many_images", f"The document contains more than {self.limits.max_assets} images.")

        ctype = (content_type or "").lower().split(";")[0].strip()
        hint = (extension_hint or "").lower().lstrip(".")
        if ctype not in EXTENSION_BY_TYPE:
            ctype = TYPE_BY_EXTENSION.get(hint, "application/octet-stream")
        width, height, image = (None, None, None)
        if ctype != "image/svg+xml":
            width, height, image = _probe(blob, self.limits.max_image_pixels)
            if width and height and width * height > self.limits.max_image_pixels:
                self.warnings.add(f"An image ({width}×{height}) exceeds the pixel limit and was kept without processing.")
        if ctype in TRANSCODE_TO_PNG and image is not None:
            try:
                out = BytesIO()
                image.convert("RGBA").save(out, "PNG")
                blob, ctype = out.getvalue(), "image/png"
            except Exception:
                self.warnings.add("A TIFF image could not be converted for browsers and was kept in its original format.")
        if image is not None:
            image.close()

        extension = EXTENSION_BY_TYPE.get(ctype, "bin")
        filename = f"{stem}.{extension}"
        classification = "review" if (width and height and (width < SMALL_IMAGE[0] or height < SMALL_IMAGE[1])) else "instructional"
        asset = Asset(
            id=filename,
            filename=filename,
            content_type=ctype,
            data=blob,
            sha256=digest,
            width=width,
            height=height,
            source_kind=self.source_kind,
            position=position,
            alt=(alt or "").strip(),
            classification=classification,
            nearest_heading=nearest_heading,
            nearest_step=nearest_step,
            slide=slide,
            relationship_id=relationship_id,
        )
        if not asset.browser_displayable:
            self.warnings.add(
                f"{filename} uses a format browsers cannot display ({ctype}); it is included in the package but shown as a placeholder."
            )
        self.assets.append(asset)
        self._by_hash[digest] = asset
        return asset
