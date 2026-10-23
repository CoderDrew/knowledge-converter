"""Allow-list sanitisation of generated HTML.

Readers escape all document text, so generated markup should already be safe.
This is the second, independent layer: every body fragment passes through
nh3 (the Rust `ammonia` sanitiser) with an allow-list of the elements and
attributes the renderers produce. Anything else — scripts, event handlers,
styles, iframes, forms, `javascript:` URLs — cannot survive, regardless of
what a document contains or what a future renderer emits by mistake.
"""
from __future__ import annotations

import re

import nh3


ALLOWED_TAGS = {
    "article", "section", "header", "aside", "div", "span", "p", "br", "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "em", "u", "s", "sub", "sup", "a", "ul", "ol", "li", "table", "thead", "tbody", "tr", "th", "td",
    "img", "figure", "figcaption",
}
ALLOWED_ATTRIBUTES = {
    "*": {"class", "id", "data-callout", "data-notes"},
    "a": {"href"},
    "img": {"src", "alt", "width", "height", "data-source-image", "loading"},
    "ol": {"start"},
    "th": {"colspan", "rowspan", "scope"},
    "td": {"colspan", "rowspan"},
}
URL_SCHEMES = {"http", "https", "mailto", "data"}
_DATA_IMAGE = re.compile(r"^data:image/(png|jpeg|gif|webp|bmp|svg\+xml);base64,[A-Za-z0-9+/=]+$")
_RELATIVE_ASSET = re.compile(r"^(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_.-]+$")
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9 _-]{0,200}$")


def _attribute_filter(tag: str, attribute: str, value: str) -> str | None:
    if attribute == "src":
        if tag != "img":
            return None
        if value.startswith("data:"):
            return value if _DATA_IMAGE.match(value) else None
        return value if _RELATIVE_ASSET.match(value) and ".." not in value else None
    if attribute == "href":
        return None if value.lower().startswith("data:") else value
    if attribute in {"class", "id", "data-callout", "data-notes"}:
        return value if _SAFE_TOKEN.match(value) else None
    if attribute in {"colspan", "rowspan", "start", "width", "height", "data-source-image"}:
        return value if value.isdigit() and len(value) <= 6 else None
    if attribute == "scope":
        return value if value in {"col", "row", "colgroup", "rowgroup"} else None
    if attribute == "loading":
        return value if value in {"lazy", "eager"} else None
    return value


def sanitize_fragment(fragment: str) -> str:
    return nh3.clean(
        fragment,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=URL_SCHEMES,
        attribute_filter=_attribute_filter,
        link_rel="noopener noreferrer",
        strip_comments=True,
    )
