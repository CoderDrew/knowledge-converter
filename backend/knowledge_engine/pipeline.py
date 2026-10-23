from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from knowledge_engine.limits import Limits
from knowledge_engine.model import Document
from knowledge_engine.packaging import write_zip
from knowledge_engine.profiles import PROFILES
from knowledge_engine.readers import READERS
from knowledge_engine.validation import validate_package


def read_document(source: Path, source_name: str, limits: Limits | None = None) -> Document:
    """Validate and parse an Office file into the document model."""
    limits = limits or Limits()
    kind = validate_package(source, source_name, limits)
    return READERS[kind](source, source_name, limits).read()


def convert_to_directory(source: Path, source_name: str, out_dir: Path, limits: Limits | None = None) -> dict:
    """Convert `source` and write every profile's output beneath `out_dir`.

    Layout::

        assets/<image files>                 shared, for the UI's asset view
        profiles/<profile>/output.html       the profile's primary HTML
        profiles/<profile>/preview.html      self-contained preview document
        profiles/<profile>/package.zip       the complete export
        summary.json                         what the API returns

    Returns the summary. Raises ConversionError for user-facing failures.
    """
    limits = limits or Limits()
    timings: dict[str, int] = {}
    started = time.perf_counter()

    kind = validate_package(source, source_name, limits)
    timings["validate"] = _elapsed(started)

    mark = time.perf_counter()
    document = READERS[kind](source, source_name, limits).read()
    timings["parse"] = _elapsed(mark)

    mark = time.perf_counter()
    assets_dir = out_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for asset in document.assets:
        (assets_dir / asset.filename).write_bytes(asset.data)

    profiles = []
    for profile in PROFILES.values():
        target = out_dir / "profiles" / profile.id
        target.mkdir(parents=True, exist_ok=True)
        output = profile.build(document)
        (target / "output.html").write_text(output.html, encoding="utf-8")
        (target / "preview.html").write_text(profile.preview(document), encoding="utf-8")
        package_size = write_zip(output.files, target / "package.zip")
        profiles.append({
            **profile.describe(),
            "html_bytes": len(output.html.encode("utf-8")),
            "package_bytes": package_size,
            "files": sorted(output.files),
        })
    timings["render"] = _elapsed(mark)
    timings["total"] = _elapsed(started)

    summary = {
        "title": document.title,
        "source": {"name": source_name, "kind": kind, "size_bytes": source.stat().st_size},
        "stats": asdict(document.stats),
        "outline": document.outline(),
        "warnings": document.warnings,
        "assets": [
            {
                "filename": asset.filename,
                "content_type": asset.content_type,
                "width": asset.width,
                "height": asset.height,
                "size_bytes": asset.size_bytes,
                "alt": asset.alt or None,
                "slide": asset.slide,
                "context": asset.nearest_heading,
                "occurrences": asset.occurrences,
                "displayable": asset.browser_displayable,
            }
            for asset in document.assets
        ],
        "profiles": profiles,
        "timings_ms": timings,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    return summary


def _elapsed(since: float) -> int:
    return round((time.perf_counter() - since) * 1000)
