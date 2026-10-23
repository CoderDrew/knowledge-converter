"""Compare the Freshservice profile against the original FS Knowledge Converter.

Usage (from backend/):
    python scripts/compare_with_original.py "C:/Projects/FS Knowledge Converter" file1.docx [file2.docx ...]

The original package is imported read-only (bytecode writing is disabled) and
its output goes to a temporary directory. For each DOCX the script compares
visible text, structural tag sequence, image order, and image bytes, then
prints a verdict. Document text is never printed; differences are reported
as counts and tag names only.
"""
from __future__ import annotations

import hashlib
import sys
import tempfile
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from knowledge_engine.pipeline import read_document  # noqa: E402
from knowledge_engine.profiles import PROFILES  # noqa: E402

STRUCTURAL = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "ol", "ul", "li", "table", "thead", "tbody", "tr", "th", "td", "img", "strong", "em", "a"}


class Shape(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.text: list[str] = []
        self.images: list[str] = []
        self._in_body = False

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self._in_body = True
        if not self._in_body:
            return
        if tag in STRUCTURAL:
            attrs = dict(attrs)
            label = tag + (f"[start={attrs['start']}]" if tag == "ol" and "start" in attrs else "")
            label += f"[{attrs['class']}]" if attrs.get("class") else ""
            self.tags.append(label)
        if tag == "img":
            self.images.append(dict(attrs).get("src", ""))

    def handle_data(self, data):
        if self._in_body and data.strip():
            self.text.extend(data.split())


def shape(markup: str) -> Shape:
    parser = Shape()
    parser.feed(markup)
    return parser


def compare(original_root: Path, source: Path) -> bool:
    sys.path.insert(0, str(original_root))
    try:
        from app.converters.docx_converter import DocxConverter as OriginalConverter  # type: ignore
    finally:
        sys.path.pop(0)

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        original_html, original_manifest, *_ = OriginalConverter(source, out).convert()
        original_images = [hashlib.sha256((out / "images" / i["filename"]).read_bytes()).hexdigest() for i in original_manifest["images"]]

    document = read_document(source, source.name)
    new_html = PROFILES["freshservice"].build(document).html
    asset_hash = {f"images/{a.filename}": a.sha256 for a in document.assets}

    old, new = shape(original_html), shape(new_html)
    new_images = [asset_hash.get(src, "?") for src in new.images]
    text_ratio = SequenceMatcher(None, old.text, new.text, autojunk=False).ratio()
    tag_ratio = SequenceMatcher(None, old.tags, new.tags, autojunk=False).ratio()

    print(f"\n== {source.name}")
    print(f"  words          original={len(old.text):5d}  new={len(new.text):5d}  similarity={text_ratio:.4f}")
    print(f"  structure tags original={len(old.tags):5d}  new={len(new.tags):5d}  similarity={tag_ratio:.4f}")
    print(f"  images         original={len(original_images):5d}  new={len(new_images):5d}  same order/bytes={original_images == new_images}")
    if old.tags != new.tags:
        matcher = SequenceMatcher(None, old.tags, new.tags, autojunk=False)
        for op, a0, a1, b0, b1 in matcher.get_opcodes():
            if op != "equal":
                print(f"  {op:7s} original{old.tags[a0:a1][:8]} -> new{new.tags[b0:b1][:8]}")
    if old.text != new.text:
        matcher = SequenceMatcher(None, old.text, new.text, autojunk=False)
        changes = [(op, a1 - a0, b1 - b0) for op, a0, a1, b0, b1 in matcher.get_opcodes() if op != "equal"]
        print(f"  text differences: {len(changes)} spans (word counts only): {changes[:10]}")
    identical = old.text == new.text and original_images == new_images
    print("  verdict:", "text and images identical" if identical else "DIFFERENCES — review above")
    return identical


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    root = Path(sys.argv[1])
    results = [compare(root, Path(arg)) for arg in sys.argv[2:]]
    sys.exit(0 if all(results) else 1)
