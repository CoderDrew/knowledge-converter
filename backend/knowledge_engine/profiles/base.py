from __future__ import annotations

import base64
import html
import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass

from knowledge_engine import __version__
from knowledge_engine.model import Asset, Document
from knowledge_engine.sanitize import sanitize_fragment


@dataclass
class ProfileOutput:
    html_filename: str
    html: str
    files: dict[str, bytes]


# Neutral reading styles used only for previewing profiles that ship unstyled
# markup, so the preview is legible. They are not part of the export.
PREVIEW_READING_CSS = """
:root{color-scheme:light}
body{font:16px/1.65 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color:#1d1d24;max-width:860px;margin:0 auto;padding:40px 28px 80px;background:#fff}
h1,h2,h3,h4{line-height:1.25;margin:1.6em 0 .55em}h1{font-size:2rem;margin-top:0}h2{font-size:1.45rem}h3{font-size:1.15rem}
img{display:block;max-width:100%;height:auto;margin:16px 0;border:1px solid #e3e3ea;border-radius:8px}
table{border-collapse:collapse;width:100%;margin:18px 0;font-size:.95rem}th,td{border:1px solid #d9d9e3;padding:8px 10px;text-align:left;vertical-align:top}th{background:#f4f4f8}
aside{margin:16px 0;padding:12px 16px;border-left:3px solid #5b4bff;background:#f5f4ff;border-radius:0 8px 8px 0}
aside[data-notes]{border-color:#9a9aa8;background:#f6f6f8;font-size:.92rem}
section{padding-bottom:12px;margin-bottom:28px;border-bottom:1px solid #ececf2}
a{color:#4433e6}li{margin:.25em 0}
"""


def data_uri(asset: Asset) -> str:
    return f"data:{asset.content_type};base64,{base64.b64encode(asset.data).decode('ascii')}"


def html_document(title: str, body: str, *, head: str = "", body_open: str = "<body>", wrap: bool = True) -> str:
    content = f"<article>\n{body}\n</article>" if wrap else body
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<meta name="generator" content="Mindjax Knowledge Converter {__version__}">\n'
        f"<title>{html.escape(title)}</title>\n{head}</head>\n{body_open}\n{content}\n</body>\n</html>\n"
    )


def generic_manifest(document: Document, profile_id: str, asset_path: str) -> bytes:
    data = {
        "version": 1,
        "generator": f"Mindjax Knowledge Converter {__version__}",
        "profile": profile_id,
        "title": document.title,
        "source": {"name": document.source_name, "kind": document.source_kind},
        "stats": asdict(document.stats),
        "assets": [
            {
                "filename": asset.filename,
                "path": f"{asset_path}{asset.filename}",
                "content_type": asset.content_type,
                "width": asset.width,
                "height": asset.height,
                "size_bytes": asset.size_bytes,
                "sha256": asset.sha256,
                "alt": asset.alt or None,
                "slide": asset.slide,
                "nearest_heading": asset.nearest_heading,
                "occurrences": asset.occurrences,
                "browser_displayable": asset.browser_displayable,
            }
            for asset in document.assets
        ],
        "warnings": document.warnings,
    }
    return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")


class OutputProfile(ABC):
    id: str
    name: str
    summary: str
    html_filename: str

    @abstractmethod
    def body(self, document: Document, *, preview: bool) -> str:
        """Unsanitised body fragment; `preview` embeds images as data URIs."""

    @abstractmethod
    def build(self, document: Document) -> ProfileOutput:
        """Files for the export package, keyed by relative path."""

    @abstractmethod
    def preview(self, document: Document) -> str:
        """A self-contained HTML document: inline styles, data-URI images."""

    def safe_body(self, document: Document, *, preview: bool = False) -> str:
        return sanitize_fragment(self.body(document, preview=preview))

    def describe(self) -> dict[str, str]:
        return {"id": self.id, "name": self.name, "summary": self.summary, "html_filename": self.html_filename}
