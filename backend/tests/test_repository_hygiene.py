"""The confidential-material guard (scripts/check_confidential.py) and the samples it allows."""
from __future__ import annotations

import importlib.util
import io
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from PIL import Image
from PIL.PngImagePlugin import PngInfo

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_confidential", REPO / "scripts" / "check_confidential.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

# A made-up term, so this file never has to contain a real blocked one.
TERMS = ({guard.term_hash("orion ledger")}, 2)
SAMPLES = REPO / "backend" / "samples"


def problems(name: str, data: bytes) -> list[str]:
    return guard.check(name, data, TERMS, guard.sample_image_hashes())


def office_bytes(members: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in members.items():
            archive.writestr(name, text)
    return buffer.getvalue()


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_repository_passes_the_guard():
    result = subprocess.run([sys.executable, "scripts/check_confidential.py"], cwd=REPO, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout


def test_committed_samples_are_generated_and_clean():
    documents = sorted(SAMPLES.glob("*.docx")) + sorted(SAMPLES.glob("*.pptx"))
    assert [p.name for p in documents] == ["sample-expense-guide.docx", "sample-expense-guide.pptx"]
    for path in [*documents, *SAMPLES.glob("*.png")]:
        assert problems(f"backend/samples/{path.name}", path.read_bytes()) == []


def test_documents_outside_samples_are_rejected():
    sample = (SAMPLES / "sample-expense-guide.docx").read_bytes()
    assert problems("docs/Training Guide.docx", sample)
    assert problems("frontend/public/demo/handout.pdf", b"%PDF-1.7")


def test_sample_without_generator_marker_is_rejected():
    fake = office_bytes({"docProps/core.xml": "<cp:coreProperties/>", "word/document.xml": "<w:t>Hello</w:t>"})
    assert problems("backend/samples/sample-real.docx", fake)


def test_blocked_terms_are_found_in_text_archives_and_metadata():
    assert problems("frontend/public/demo/preview.html", b"<h1>Orion  Ledger: month end</h1>")
    assert problems("frontend/public/demo/result.json", b'{"title": "ORION-LEDGER"}')
    archive = office_bytes({"document.html": "<p>orion ledger</p>"})
    assert problems("frontend/public/demo/package.zip", archive)

    info = PngInfo(); info.add_text("Comment", "Orion Ledger export")
    image = io.BytesIO(); Image.new("RGB", (4, 4)).save(image, "PNG", pnginfo=info)
    assert any("metadata" in p for p in problems("backend/samples/sample-shot.png", image.getvalue()))

    assert problems("frontend/public/demo/preview.html", b"<h1>Orion</h1><p>Ledger</p>") == []


def test_demo_images_must_come_from_the_samples():
    sample_png = (SAMPLES / "sample-screenshot.png").read_bytes()
    assert problems("frontend/public/demo/images/image-001.png", sample_png) == []
    other = io.BytesIO(); Image.new("RGB", (8, 8), "red").save(other, "PNG")
    assert problems("frontend/public/demo/images/image-001.png", other.getvalue())


def test_findings_never_echo_the_term():
    assert all("orion" not in p.lower() for p in problems("notes.md", b"orion ledger"))
