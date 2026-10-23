"""Freshservice knowledge-article profile.

Reproduces the FS Knowledge Converter's output contract: `article.html` with
its inline article styles and `callout` classes, images in `images/` with
`data-source-image` ordinals and "Instructional image N" alt text, a
`manifest.json` recording each image's nearest heading and step, and a
`conversion-report.html`. Everything vendor-specific lives in this file.
"""
from __future__ import annotations

import html
import json
from dataclasses import asdict

from knowledge_engine.model import Document
from knowledge_engine.profiles.base import OutputProfile, ProfileOutput, data_uri
from knowledge_engine.profiles.html_writer import HtmlConventions, HtmlWriter


ARTICLE_CSS = (
    "body{font-family:Arial,sans-serif;line-height:1.55;color:#172b4d;max-width:900px;margin:32px auto;padding:0 24px}"
    "h1,h2,h3{color:#12344d}img{display:block;max-width:100%;height:auto;margin:18px 0;border:1px solid #dfe3e8;border-radius:6px}"
    "table{border-collapse:collapse;width:100%;margin:18px 0}th,td{border:1px solid #cfd7df;padding:9px;text-align:left;vertical-align:top}"
    "th{background:#f2f5f7}.callout{padding:12px 16px;border-left:4px solid #2c5cc5;background:#f2f7ff}"
    ".warning,.caution{border-color:#d82c0d;background:#fff4f2}.tip{border-color:#00a886;background:#effffb}"
    ".conversion-warning{color:#b42318}.speaker-notes{color:#5e6c84;font-size:.92em}"
)


class FreshserviceProfile(OutputProfile):
    id = "freshservice"
    name = "Freshservice Article"
    summary = "Knowledge-base article markup with an image manifest and conversion report, matching the original FS converter."
    html_filename = "article.html"

    def _conventions(self, preview: bool) -> HtmlConventions:
        return HtmlConventions(
            image_src=data_uri if preview else (lambda asset: f"images/{asset.filename}"),
            image_alt=lambda asset, number: f"Instructional image {number}",
            image_attrs=lambda asset, number: f' data-source-image="{number}"',
            callout=lambda kind, body: f'<p class="callout {kind}">{body}</p>',
            notice=lambda text: f'<span class="conversion-warning">{html.escape(text)}</span>',
            unsupported_image=lambda asset: f'<span class="conversion-warning">[Unsupported image format: {html.escape(asset.filename)}]</span>',
            header_scope=False,
            notes_class="speaker-notes",
        )

    def body(self, document: Document, *, preview: bool) -> str:
        return HtmlWriter(document, self._conventions(preview)).body()

    def _page(self, document: Document, *, preview: bool) -> str:
        body = self.safe_body(document, preview=preview)
        return (
            '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f"<title>{html.escape(document.title)}</title>\n<style>{ARTICLE_CSS}</style>\n</head><body>{body}</body></html>"
        )

    def _warnings(self, document: Document) -> list[str]:
        warnings = list(document.warnings)
        for number, asset in enumerate(document.assets, 1):
            if asset.classification == "review":
                warnings.append(f"Image {number} is small and was included for human review.")
        return warnings

    def _manifest(self, document: Document) -> dict:
        images = []
        for number, asset in enumerate(document.assets, 1):
            images.append({
                "id": number,
                "filename": asset.filename,
                "source": asset.source_kind,
                "source_relationship_id": asset.relationship_id,
                "document_position": asset.position,
                "nearest_heading": asset.nearest_heading,
                "nearest_step": asset.nearest_step,
                "slide": asset.slide,
                "width": asset.width,
                "height": asset.height,
                "content_type": asset.content_type,
                "classification": asset.classification,
                "confidence": None,
                "description": asset.alt or f"Instructional image {number}",
                "sha256": asset.sha256,
                "size_bytes": asset.size_bytes,
                "occurrences": asset.occurrences,
            })
        return {"version": 1, "source": document.source_name, "images": images, "warnings": self._warnings(document)}

    def _report(self, document: Document) -> str:
        warnings = "".join(f"<li>{html.escape(item)}</li>" for item in self._warnings(document)) or "<li>None</li>"
        stats = "".join(
            f"<li>{html.escape(key.replace('_', ' ').title())}: {value}</li>" for key, value in asdict(document.stats).items()
        )
        return (
            '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Conversion report</title>'
            "<style>body{font-family:Arial,sans-serif;max-width:800px;margin:40px auto;line-height:1.5;color:#172b4d}</style></head><body>"
            f"<h1>Conversion report</h1><p><strong>Source:</strong> {html.escape(document.source_name)}</p>"
            f"<h2>{html.escape(document.source_kind.upper())}</h2><ul>{stats}</ul>"
            "<h2>Output</h2><p>article.html, manifest.json, extracted images, and this report.</p>"
            f"<h2>Warnings</h2><ul>{warnings}</ul></body></html>"
        )

    def build(self, document: Document) -> ProfileOutput:
        page = self._page(document, preview=False)
        files = {
            self.html_filename: page.encode("utf-8"),
            "manifest.json": json.dumps(self._manifest(document), indent=2, ensure_ascii=False).encode("utf-8"),
            "conversion-report.html": self._report(document).encode("utf-8"),
        }
        for asset in document.assets:
            files[f"images/{asset.filename}"] = asset.data
        return ProfileOutput(self.html_filename, page, files)

    def preview(self, document: Document) -> str:
        return self._page(document, preview=True)
