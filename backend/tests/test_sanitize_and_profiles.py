import json
import re
import zipfile
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path

import pytest

from knowledge_engine.pipeline import convert_to_directory, read_document
from knowledge_engine.profiles import PROFILES
from knowledge_engine.sanitize import sanitize_fragment


@pytest.mark.parametrize("hostile, forbidden", [
    ("<script>alert(1)</script>", "<script"),
    ('<img src="x.png" onerror="alert(1)">', "onerror"),
    ('<a href="javascript:alert(1)">x</a>', "javascript:"),
    ('<a href="data:text/html;base64,PHNjcmlwdD4=">x</a>', "data:text/html"),
    ('<iframe src="https://example.com"></iframe>', "<iframe"),
    ('<p style="background:url(https://track.example/p)">x</p>', "style="),
    ('<img src="https://track.example/pixel.gif">', "track.example"),
    ('<img src="../../etc/passwd">', "passwd"),
    ('<form action="https://evil.example"><input></form>', "<form"),
    ('<svg><script>alert(1)</script></svg>', "<svg"),
    ('<img src="data:text/html;base64,PHNjcmlwdD4=">', "data:text/html"),
])
def test_sanitizer_removes_active_content(hostile: str, forbidden: str):
    assert forbidden not in sanitize_fragment(hostile)


def test_sanitizer_keeps_expected_markup():
    fragment = (
        '<h2>T</h2><p class="callout tip">x <strong>b</strong> <a href="https://a.example/">l</a></p>'
        '<ol start="3"><li>i</li></ol><table><thead><tr><th scope="col" colspan="2">h</th></tr></thead></table>'
        '<img src="images/image-001.png" alt="a" data-source-image="1"><img src="data:image/png;base64,iVBORw0KGgo=" alt="d">'
    )
    clean = sanitize_fragment(fragment)
    for expected in ['class="callout tip"', 'href="https://a.example/"', 'start="3"', 'colspan="2"', 'src="images/image-001.png"',
                     'data-source-image="1"', 'src="data:image/png;base64,iVBORw0KGgo="', 'rel="noopener noreferrer"']:
        assert expected in clean


class Refs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "img":
            self.refs.append(attrs["src"])
        if tag == "link":
            self.refs.append(attrs["href"])
        if tag == "script":
            self.refs.append("SCRIPT")


def refs(markup: str) -> list[str]:
    parser = Refs(); parser.feed(markup)
    return parser.refs


@pytest.mark.parametrize("profile_id", list(PROFILES))
@pytest.mark.parametrize("fixture", ["sample_docx", "rich_pptx"])
def test_every_package_reference_resolves_inside_the_zip(profile_id: str, fixture: str, request, tmp_path: Path):
    source = request.getfixturevalue(fixture)
    summary = convert_to_directory(source, source.name, tmp_path / "out")
    package = tmp_path / "out" / "profiles" / profile_id / "package.zip"
    with zipfile.ZipFile(package) as archive:
        names = set(archive.namelist())
        page = archive.read(PROFILES[profile_id].html_filename).decode()
        manifest = json.loads(archive.read("manifest.json"))
    assert "manifest.json" in names
    found = refs(page)
    assert found, "expected at least one image reference"
    assert "SCRIPT" not in found
    for ref in found:
        assert ref.startswith("data:image/") or ref in names, ref
    assert len(manifest.get("assets", manifest.get("images"))) == len(summary["assets"])
    assert all(not n.startswith(("/", "..")) and ".." not in n.split("/") for n in names)


@pytest.mark.parametrize("profile_id", list(PROFILES))
def test_previews_are_self_contained(profile_id: str, rich_pptx: Path):
    document = read_document(rich_pptx, rich_pptx.name)
    preview = PROFILES[profile_id].preview(document)
    for ref in refs(preview):
        assert ref.startswith("data:image/"), ref
    assert not re.search(r"<(script|iframe|object|embed|link)\b", preview)


def test_clean_profile_is_class_and_style_free(sample_docx: Path):
    html = PROFILES["clean"].build(read_document(sample_docx, sample_docx.name)).html
    body = html.split("<body>", 1)[1]
    assert "class=" not in body and "style" not in body
    assert "<aside data-callout=\"tip\">" in body


def test_freshservice_manifest_matches_original_contract(sample_docx: Path):
    files = PROFILES["freshservice"].build(read_document(sample_docx, sample_docx.name)).files
    manifest = json.loads(files["manifest.json"])
    image = manifest["images"][0]
    for key in ["id", "filename", "source", "source_relationship_id", "document_position", "nearest_heading", "nearest_step",
                "width", "height", "content_type", "classification", "confidence", "description", "sha256", "size_bytes"]:
        assert key in image
    assert image["description"] == "Instructional image 1"
    assert {"article.html", "conversion-report.html", "images/image-001.png"} <= set(files)


def test_zip_round_trip_bytes_match_assets(sample_docx: Path, tmp_path: Path):
    document = read_document(sample_docx, sample_docx.name)
    convert_to_directory(sample_docx, sample_docx.name, tmp_path / "o")
    with zipfile.ZipFile(BytesIO((tmp_path / "o/profiles/assets/package.zip").read_bytes())) as archive:
        assert archive.read("assets/images/image-001.png") == document.assets[0].data
        assert archive.testzip() is None
