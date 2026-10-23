"""Format-neutral document model.

Readers translate DOCX/PPTX structure into these nodes; output profiles render
them. Nothing here knows about Word, PowerPoint, HTML, or any vendor, which is
what lets new readers and new profiles be added independently.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Union


# ---------------------------------------------------------------- inlines


@dataclass
class Text:
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    vertical: Literal["sup", "sub"] | None = None

    def same_format(self, other: "Text") -> bool:
        return (self.bold, self.italic, self.underline, self.strike, self.vertical) == (
            other.bold, other.italic, other.underline, other.strike, other.vertical
        )


@dataclass
class LineBreak:
    pass


@dataclass
class Link:
    href: str
    children: list["Inline"] = field(default_factory=list)


@dataclass
class ImageRef:
    asset_id: str
    alt: str


@dataclass
class Notice:
    """A visible marker for content the converter could not represent."""

    text: str


Inline = Union[Text, LineBreak, Link, ImageRef, Notice]


# ----------------------------------------------------------------- blocks


@dataclass
class Heading:
    level: int
    inlines: list[Inline]


@dataclass
class Paragraph:
    inlines: list[Inline]
    callout: Literal["note", "tip", "warning", "caution"] | None = None


@dataclass
class ListItem:
    inlines: list[Inline]
    children: list["ListBlock"] = field(default_factory=list)


@dataclass
class ListBlock:
    ordered: bool
    items: list[ListItem] = field(default_factory=list)
    start: int | None = None


@dataclass
class TableCell:
    lines: list[list[Inline]]
    colspan: int = 1
    rowspan: int = 1


@dataclass
class TableRow:
    cells: list[TableCell]
    header: bool = False


@dataclass
class Table:
    rows: list[TableRow]


@dataclass
class Section:
    """A titled group of blocks, e.g. one presentation slide."""

    number: int
    label: str
    title: list[Inline] | None
    blocks: list["Block"] = field(default_factory=list)
    notes: list[list[Inline]] = field(default_factory=list)


Block = Union[Heading, Paragraph, ListBlock, Table, Section]


# ----------------------------------------------------------------- assets


BROWSER_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml", "image/bmp"}


@dataclass
class Asset:
    id: str
    filename: str
    content_type: str
    data: bytes
    sha256: str
    width: int | None
    height: int | None
    source_kind: str
    position: int
    alt: str
    classification: Literal["instructional", "review"] = "instructional"
    nearest_heading: str | None = None
    nearest_step: str | None = None
    slide: int | None = None
    relationship_id: str | None = None
    occurrences: int = 1

    @property
    def size_bytes(self) -> int:
        return len(self.data)

    @property
    def browser_displayable(self) -> bool:
        return self.content_type in BROWSER_IMAGE_TYPES


# --------------------------------------------------------------- document


@dataclass
class DocumentStats:
    headings: int = 0
    paragraphs: int = 0
    lists: int = 0
    list_items: int = 0
    tables: int = 0
    images: int = 0
    slides: int = 0
    words: int = 0


@dataclass
class Document:
    title: str
    source_name: str
    source_kind: str
    blocks: list[Block]
    assets: list[Asset]
    warnings: list[str]
    stats: DocumentStats

    def asset(self, asset_id: str) -> Asset | None:
        return next((a for a in self.assets if a.id == asset_id), None)

    def outline(self) -> list[dict]:
        """Headings and slide titles in reading order, for navigation."""
        items: list[dict] = []
        for block in self.blocks:
            if isinstance(block, Heading):
                items.append({"level": block.level, "text": plain_text(block.inlines)})
            elif isinstance(block, Section):
                title = plain_text(block.title) if block.title else block.label
                items.append({"level": 2, "text": title, "label": block.label})
        return items


def plain_text(inlines: list[Inline] | None) -> str:
    if not inlines:
        return ""
    parts: list[str] = []
    for node in inlines:
        if isinstance(node, Text):
            parts.append(node.text)
        elif isinstance(node, LineBreak):
            parts.append(" ")
        elif isinstance(node, Link):
            parts.append(plain_text(node.children))
    return " ".join("".join(parts).split())


def has_visible_content(inlines: list[Inline]) -> bool:
    for node in inlines:
        if isinstance(node, Text) and node.text.strip():
            return True
        if isinstance(node, (ImageRef, Notice)):
            return True
        if isinstance(node, Link) and has_visible_content(node.children):
            return True
    return False


def normalize_inlines(inlines: list[Inline]) -> list[Inline]:
    """Merge adjacent same-format text and trim leading/trailing breaks."""
    merged: list[Inline] = []
    for node in inlines:
        if isinstance(node, Link):
            node = Link(node.href, normalize_inlines(node.children))
        last = merged[-1] if merged else None
        if isinstance(node, Text) and isinstance(last, Text) and last.same_format(node):
            merged[-1] = Text(last.text + node.text, last.bold, last.italic, last.underline, last.strike, last.vertical)
        elif isinstance(node, Text) and not node.text:
            continue
        else:
            merged.append(node)
    while merged and isinstance(merged[0], LineBreak):
        merged.pop(0)
    while merged and isinstance(merged[-1], LineBreak):
        merged.pop()
    return merged
