import zipfile
from pathlib import Path

import pytest

from knowledge_engine.errors import ConversionError
from knowledge_engine.limits import Limits
from knowledge_engine.validation import validate_package
from tests.conftest import rezip


def code_of(path: Path, name: str | None = None, limits: Limits | None = None) -> str:
    with pytest.raises(ConversionError) as raised:
        validate_package(path, name or path.name, limits or Limits())
    return raised.value.code


def test_valid_files_report_their_kind(sample_docx: Path, sample_pptx: Path):
    assert validate_package(sample_docx, sample_docx.name, Limits()) == "docx"
    assert validate_package(sample_pptx, sample_pptx.name, Limits()) == "pptx"


@pytest.mark.parametrize("name, code", [
    ("notes.txt", "unsupported_type"),
    ("report.pdf", "unsupported_type"),
    ("legacy.doc", "legacy_format"),
    ("legacy.ppt", "legacy_format"),
    ("macro.docm", "macro_enabled"),
    ("noext", "unsupported_type"),
])
def test_extension_allow_list(tmp_path: Path, name: str, code: str):
    path = tmp_path / "upload"; path.write_bytes(b"irrelevant")
    assert code_of(path, name) == code


def test_empty_file(tmp_path: Path):
    path = tmp_path / "empty.docx"; path.write_bytes(b"")
    assert code_of(path) == "empty_file"


def test_renamed_text_file_is_rejected_by_content(tmp_path: Path):
    path = tmp_path / "fake.docx"; path.write_text("just some text pretending to be a document")
    assert code_of(path) == "not_office_file"


def test_ole_container_is_reported_as_encrypted_or_legacy(tmp_path: Path):
    path = tmp_path / "protected.docx"; path.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 512)
    assert code_of(path) == "encrypted_or_legacy"


def test_truncated_archive_is_corrupted(sample_docx: Path, tmp_path: Path):
    data = sample_docx.read_bytes()
    path = tmp_path / "truncated.docx"; path.write_bytes(data[: len(data) // 2])
    assert code_of(path) == "corrupted"


def test_zip_that_is_not_ooxml(tmp_path: Path):
    path = tmp_path / "plain.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("hello.txt", "hi")
    assert code_of(path) == "not_office_file"


def test_extension_content_mismatch_is_explained(sample_pptx: Path, tmp_path: Path):
    renamed = tmp_path / "deck.docx"; renamed.write_bytes(sample_pptx.read_bytes())
    assert code_of(renamed) == "type_mismatch"


def test_macro_enabled_content_type_is_rejected(sample_docx: Path, tmp_path: Path):
    with zipfile.ZipFile(sample_docx) as archive:
        types = archive.read("[Content_Types].xml").decode()
    types = types.replace("wordprocessingml.document.main+xml", "PLACEHOLDER").replace(
        "application/vnd.openxmlformats-officedocument.PLACEHOLDER", "application/vnd.ms-word.document.macroEnabled.main+xml"
    )
    path = rezip(sample_docx, tmp_path / "macro.docx", replace={"[Content_Types].xml": types.encode()})
    assert code_of(path) == "macro_enabled"


def test_vba_project_part_is_rejected(sample_docx: Path, tmp_path: Path):
    path = rezip(sample_docx, tmp_path / "vba.docx", extra={"word/vbaProject.bin": b"\0" * 10})
    assert code_of(path) == "macro_enabled"


@pytest.mark.parametrize("member", ["../evil.txt", "/abs/evil.txt", "word\\..\\evil.txt", "C:/evil.txt"])
def test_path_traversal_members_are_rejected(sample_docx: Path, tmp_path: Path, member: str):
    path = tmp_path / "traversal.docx"
    with zipfile.ZipFile(sample_docx) as src, zipfile.ZipFile(path, "w") as dst:
        for info in src.infolist():
            dst.writestr(info, src.read(info.filename))
        info = zipfile.ZipInfo("placeholder"); info.filename = member
        dst.writestr(info, b"x")
    assert code_of(path) == "unsafe_archive"


def test_entry_count_limit(sample_docx: Path, tmp_path: Path):
    path = rezip(sample_docx, tmp_path / "many.docx", extra={f"customXml/item{i}.xml": b"<a/>" for i in range(60)})
    assert code_of(path, limits=Limits(max_archive_entries=50)) == "archive_limits"


def test_decompression_bomb_total_size(sample_docx: Path, tmp_path: Path):
    path = rezip(sample_docx, tmp_path / "bomb.docx", extra={"customXml/bomb.xml": b"\0" * (12 * 1024 * 1024)})
    assert code_of(path, limits=Limits(max_uncompressed_bytes=8 * 1024 * 1024)) == "archive_limits"


def test_decompression_bomb_ratio(sample_docx: Path, tmp_path: Path):
    path = rezip(sample_docx, tmp_path / "ratio.docx", extra={"customXml/bomb.xml": b"\0" * (11 * 1024 * 1024)})
    assert code_of(path) == "archive_limits"


def test_upload_size_limit(sample_docx: Path):
    assert code_of(sample_docx, limits=Limits(max_upload_bytes=1024)) == "file_too_large"


def test_external_entities_are_not_resolved(sample_docx: Path, tmp_path: Path):
    secret = tmp_path / "secret.txt"; secret.write_text("TOP-SECRET")
    with zipfile.ZipFile(sample_docx) as archive:
        document_xml = archive.read("word/document.xml").decode()
    doctype = f'<!DOCTYPE w:document [<!ENTITY xxe SYSTEM "{secret.as_uri()}">]>'
    hostile = document_xml.replace("?>", "?>" + doctype, 1).replace("Cash Management</w:t>", "&xxe;</w:t>", 1)
    path = rezip(sample_docx, tmp_path / "xxe.docx", replace={"word/document.xml": hostile.encode()})
    from knowledge_engine.pipeline import read_document
    from knowledge_engine.profiles import PROFILES
    try:
        html = PROFILES["clean"].build(read_document(path, path.name)).html
    except ConversionError:
        return  # rejecting the file is also acceptable
    assert "TOP-SECRET" not in html
