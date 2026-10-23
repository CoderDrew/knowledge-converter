from __future__ import annotations

from knowledge_engine.model import Document
from knowledge_engine.profiles.base import (
    PREVIEW_READING_CSS, OutputProfile, ProfileOutput, data_uri, generic_manifest, html_document,
)
from knowledge_engine.profiles.html_writer import HtmlConventions, HtmlWriter


class CleanHtmlProfile(OutputProfile):
    """Semantic, unstyled, class-free markup in a single portable file.

    Images are embedded as data URIs so `document.html` works on its own when
    pasted into a CMS or opened directly; the package also carries the
    original image files for systems that prefer uploaded media.
    """

    id = "clean"
    name = "Clean HTML"
    summary = "Semantic, style-free markup in one self-contained file. Ideal for websites and CMS editors."
    html_filename = "document.html"

    def _conventions(self) -> HtmlConventions:
        return HtmlConventions(image_src=data_uri)

    def body(self, document: Document, *, preview: bool) -> str:
        return HtmlWriter(document, self._conventions()).body()

    def build(self, document: Document) -> ProfileOutput:
        page = html_document(document.title, self.safe_body(document))
        files = {self.html_filename: page.encode("utf-8"), "manifest.json": generic_manifest(document, self.id, "assets/")}
        for asset in document.assets:
            files[f"assets/{asset.filename}"] = asset.data
        return ProfileOutput(self.html_filename, page, files)

    def preview(self, document: Document) -> str:
        return html_document(document.title, self.safe_body(document, preview=True), head=f"<style>{PREVIEW_READING_CSS}</style>\n")
