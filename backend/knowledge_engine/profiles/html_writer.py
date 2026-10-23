"""Renders the document model to an HTML body fragment.

Profiles configure this writer rather than re-implementing traversal, so a
new output format only decides markup conventions, image references, and the
surrounding document shell.
"""
from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Callable

from knowledge_engine.model import (
    Asset, Block, Document, Heading, ImageRef, Inline, LineBreak, Link, ListBlock, Notice, Paragraph, Section, Table,
    Text,
)


@dataclass
class HtmlConventions:
    image_src: Callable[[Asset], str]
    image_alt: Callable[[Asset, int], str] = lambda asset, number: f"Image {number}"
    callout: Callable[[str, str], str] = lambda kind, body: f'<aside data-callout="{kind}"><p>{body}</p></aside>'
    notice: Callable[[str], str] = lambda text: f"<em>{html.escape(text)}</em>"
    unsupported_image: Callable[[Asset], str] = lambda asset: f"<em>[Image {html.escape(asset.filename)} uses a format browsers cannot display]</em>"
    image_attrs: Callable[[Asset, int], str] = lambda asset, number: ""
    header_scope: bool = True
    section_class: str | None = None
    notes_class: str | None = None
    include_notes: bool = True
    section_heading_level: int = 2
    lazy_images: bool = False
    intrinsic_size: bool = False
    block_separator: str = "\n"


class HtmlWriter:
    def __init__(self, document: Document, conventions: HtmlConventions) -> None:
        self.doc = document
        self.c = conventions
        self.numbers = {asset.id: index for index, asset in enumerate(document.assets, 1)}

    def body(self) -> str:
        return self.c.block_separator.join(self._block(block) for block in self.doc.blocks)

    # --------------------------------------------------------------- blocks

    def _block(self, block: Block) -> str:
        if isinstance(block, Heading):
            level = max(1, min(block.level, 6))
            return f"<h{level}>{self._inlines(block.inlines)}</h{level}>"
        if isinstance(block, Paragraph):
            body = self._inlines(block.inlines)
            return self.c.callout(block.callout, body) if block.callout else f"<p>{body}</p>"
        if isinstance(block, ListBlock):
            return self._list(block)
        if isinstance(block, Table):
            return self._table(block)
        if isinstance(block, Section):
            return self._section(block)
        return ""

    def _list(self, block: ListBlock) -> str:
        tag = "ol" if block.ordered else "ul"
        start = f' start="{block.start}"' if block.ordered and block.start and block.start != 1 else ""
        items = []
        for item in block.items:
            nested = "".join(self._list(child) for child in item.children)
            items.append(f"<li>{self._inlines(item.inlines)}{nested}</li>")
        return f"<{tag}{start}>{''.join(items)}</{tag}>"

    def _table(self, table: Table) -> str:
        head_rows: list[str] = []
        body_rows: list[str] = []
        in_head = True
        for row in table.rows:
            header = row.header and in_head
            in_head = header
            tag = "th" if header else "td"
            cells = []
            for cell in row.cells:
                attrs = ""
                if cell.colspan > 1:
                    attrs += f' colspan="{cell.colspan}"'
                if cell.rowspan > 1:
                    attrs += f' rowspan="{cell.rowspan}"'
                if header and self.c.header_scope:
                    attrs += ' scope="col"'
                content = "<br>".join(self._inlines(line) for line in cell.lines)
                cells.append(f"<{tag}{attrs}>{content}</{tag}>")
            (head_rows if header else body_rows).append(f"<tr>{''.join(cells)}</tr>")
        head = f"<thead>{''.join(head_rows)}</thead>" if head_rows else ""
        return f"<table>{head}<tbody>{''.join(body_rows)}</tbody></table>"

    def _section(self, section: Section) -> str:
        level = self.c.section_heading_level
        title = self._inlines(section.title) if section.title else html.escape(section.label)
        cls = f' class="{self.c.section_class}"' if self.c.section_class else ""
        parts = [f'<section id="slide-{section.number}"{cls}>', f"<h{level}>{title}</h{level}>"]
        parts.extend(self._block(block) for block in section.blocks)
        if section.notes and self.c.include_notes:
            notes_cls = f' class="{self.c.notes_class}"' if self.c.notes_class else ' data-notes="speaker"'
            lines = "".join(f"<p>{self._inlines(line)}</p>" for line in section.notes)
            parts.append(f"<aside{notes_cls}><h{min(level + 1, 6)}>Speaker notes</h{min(level + 1, 6)}>{lines}</aside>")
        parts.append("</section>")
        return self.c.block_separator.join(parts)

    # -------------------------------------------------------------- inlines

    def _inlines(self, inlines: list[Inline] | None) -> str:
        return "".join(self._inline(node) for node in inlines or [])

    def _inline(self, node: Inline) -> str:
        if isinstance(node, Text):
            value = html.escape(node.text).replace("\n", "<br>")
            if node.vertical:
                value = f"<{node.vertical}>{value}</{node.vertical}>"
            if node.strike:
                value = f"<s>{value}</s>"
            if node.underline:
                value = f"<u>{value}</u>"
            if node.italic:
                value = f"<em>{value}</em>"
            if node.bold:
                value = f"<strong>{value}</strong>"
            return value
        if isinstance(node, LineBreak):
            return "<br>"
        if isinstance(node, Link):
            return f'<a href="{html.escape(node.href, quote=True)}">{self._inlines(node.children)}</a>'
        if isinstance(node, ImageRef):
            asset = self.doc.asset(node.asset_id)
            if asset is None:
                return self.c.notice("[Missing image]")
            if not asset.browser_displayable:
                return self.c.unsupported_image(asset)
            number = self.numbers[asset.id]
            alt = node.alt or self.c.image_alt(asset, number)
            dims = ""
            if self.c.intrinsic_size and asset.width and asset.height:
                dims = f' width="{asset.width}" height="{asset.height}"'
            lazy = ' loading="lazy"' if self.c.lazy_images else ""
            return (
                f'<img src="{html.escape(self.c.image_src(asset), quote=True)}" alt="{html.escape(alt, quote=True)}"'
                f"{dims}{lazy}{self.c.image_attrs(asset, number)}>"
            )
        if isinstance(node, Notice):
            return self.c.notice(node.text)
        return ""
