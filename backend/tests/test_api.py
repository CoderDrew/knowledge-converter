import dataclasses
import io
import time
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.config import Settings
from api.main import create_app


DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.fixture
def client(settings: Settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def upload(client: TestClient, path: Path, name: str | None = None):
    with path.open("rb") as stream:
        return client.post("/api/conversions", files={"file": (name or path.name, stream, DOCX_TYPE)})


def job_dirs(settings: Settings) -> list[Path]:
    return [p for p in settings.work_dir.iterdir() if p.is_dir()]


def test_health_reports_limits_and_profiles(client: TestClient):
    data = client.get("/api/health").json()
    assert data["status"] == "ok"
    assert data["limits"]["max_upload_bytes"] == 20 * 1024 * 1024
    assert [p["id"] for p in data["profiles"]] == ["clean", "assets", "freshservice"]


def test_full_docx_flow(client: TestClient, sample_docx: Path, settings: Settings):
    response = upload(client, sample_docx)
    assert response.status_code == 201, response.text
    data = response.json()
    job = data["id"]
    assert len(job) == 32 and data["title"] == "Cash Management"
    assert data["source"] == {"name": "Cash Management.docx", "kind": "docx", "size_bytes": sample_docx.stat().st_size}
    assert data["stats"]["images"] == 1 and data["outline"][0]["text"] == "Cash Management"
    assert {"validate", "parse", "render", "total"} <= set(data["timings_ms"])

    assert client.get(f"/api/conversions/{job}").json()["id"] == job

    preview = client.get(f"/api/conversions/{job}/profiles/assets/preview")
    assert preview.status_code == 200
    csp = preview.headers["content-security-policy"]
    assert "sandbox" in csp and "default-src 'none'" in csp and "script-src" not in csp
    assert "frame-ancestors http://localhost:3000" in csp
    assert preview.headers["x-content-type-options"] == "nosniff"

    source = client.get(f"/api/conversions/{job}/profiles/clean/source")
    assert source.headers["content-type"].startswith("text/plain")
    assert "<h1>Cash Management</h1>" in source.text

    html = client.get(f"/api/conversions/{job}/profiles/freshservice/html")
    assert 'attachment; filename="cash-management-freshservice.html"' == html.headers["content-disposition"]

    package = client.get(f"/api/conversions/{job}/profiles/assets/package")
    assert package.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(package.content)) as archive:
        assert {"index.html", "assets/styles.css", "assets/images/image-001.png", "manifest.json"} <= set(archive.namelist())

    asset = client.get(f"/api/conversions/{job}/assets/image-001.png")
    assert asset.headers["content-type"] == "image/png"
    assert "sandbox" in asset.headers["content-security-policy"]
    assert asset.headers["cache-control"] == "no-store"

    # The upload itself is gone as soon as conversion finishes.
    root = settings.work_dir / job
    assert not (root / "upload").exists()
    assert not any(p.suffix in {".docx", ".pptx"} for p in root.rglob("*"))

    assert client.delete(f"/api/conversions/{job}").status_code == 204
    assert client.get(f"/api/conversions/{job}").status_code == 404
    assert not root.exists()


def test_pptx_flow(client: TestClient, rich_pptx: Path):
    response = upload(client, rich_pptx)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["source"]["kind"] == "pptx" and data["stats"]["slides"] == 4
    assert data["assets"][0]["slide"] == 3


@pytest.mark.parametrize("name, body, status, code", [
    ("notes.txt", b"text", 415, "unsupported_type"),
    ("old.doc", b"\xd0\xcf\x11\xe0", 415, "legacy_format"),
    ("fake.docx", b"not really a zip", 422, "not_office_file"),
    ("broken.pptx", b"PK\x03\x04garbage-after-header", 422, "corrupted"),
])
def test_invalid_uploads_are_rejected_and_cleaned_up(client: TestClient, settings: Settings, name, body, status, code):
    response = client.post("/api/conversions", files={"file": (name, body, "application/octet-stream")})
    assert response.status_code == status
    assert response.json()["detail"]["code"] == code
    assert job_dirs(settings) == []


def test_missing_file_field(client: TestClient):
    response = client.post("/api/conversions", data={"other": "x"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "missing_file"


def test_client_supplied_filename_cannot_escape(client: TestClient, sample_docx: Path, settings: Settings):
    response = upload(client, sample_docx, name="../../..\\windows\\evil.docx")
    assert response.status_code == 201
    assert response.json()["source"]["name"] == "evil.docx"
    assert all(p.parent == settings.work_dir for p in job_dirs(settings))


def test_oversized_upload_rejected_by_content_length(settings: Settings, sample_docx: Path):
    small = dataclasses.replace(settings, max_upload_mb=1)
    with TestClient(create_app(small)) as client:
        payload = b"PK\x03\x04" + b"\0" * (3 * 1024 * 1024)
        response = client.post("/api/conversions", files={"file": ("big.docx", payload, DOCX_TYPE)})
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "file_too_large"
    assert job_dirs(small) == []


def test_oversized_streamed_upload_is_cut_off(settings: Settings):
    small = dataclasses.replace(settings, max_upload_mb=1)
    boundary = "kcboundary"

    def body():
        yield f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="big.docx"\r\nContent-Type: {DOCX_TYPE}\r\n\r\n'.encode()
        for _ in range(40):
            yield b"\0" * (128 * 1024)
        yield f"\r\n--{boundary}--\r\n".encode()

    with TestClient(create_app(small)) as client:
        response = client.post("/api/conversions", content=body(), headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    assert response.status_code == 413
    assert job_dirs(small) == []


def test_file_just_over_limit_but_within_multipart_allowance(settings: Settings, sample_docx: Path):
    tiny = dataclasses.replace(settings, max_upload_mb=0)  # 0 MB: every real file is too large
    with TestClient(create_app(tiny)) as client:
        response = upload(client, sample_docx)
    assert response.status_code == 413


def test_rate_limit(settings: Settings, sample_docx: Path):
    limited = dataclasses.replace(settings, rate_limit_per_minute=2)
    with TestClient(create_app(limited)) as client:
        assert upload(client, sample_docx).status_code == 201
        assert upload(client, sample_docx).status_code == 201
        blocked = upload(client, sample_docx)
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) >= 1


def test_results_expire(settings: Settings, sample_docx: Path):
    short = dataclasses.replace(settings, result_ttl_s=1)
    with TestClient(create_app(short)) as client:
        job = upload(client, sample_docx).json()["id"]
        assert client.get(f"/api/conversions/{job}").status_code == 200
        time.sleep(1.2)
        assert client.get(f"/api/conversions/{job}").status_code == 404
    assert not (short.work_dir / job).exists()


def test_startup_and_shutdown_purge_leftovers(settings: Settings, sample_docx: Path):
    stale = settings.work_dir / ("a" * 32)
    (stale / "out").mkdir(parents=True)
    with TestClient(create_app(settings)) as client:
        assert not stale.exists()
        upload(client, sample_docx)
        assert job_dirs(settings)
    assert job_dirs(settings) == []


@pytest.mark.parametrize("path", [
    "/api/conversions/not-a-job",
    "/api/conversions/../../etc/passwd",
    "/api/conversions/" + "0" * 32,
])
def test_unknown_or_malicious_job_ids(client: TestClient, path: str):
    assert client.get(path).status_code == 404


def test_asset_and_profile_lookups_are_strict(client: TestClient, sample_docx: Path):
    job = upload(client, sample_docx).json()["id"]
    assert client.get(f"/api/conversions/{job}/assets/..%2Fsummary.json").status_code == 404
    assert client.get(f"/api/conversions/{job}/assets/summary.json").status_code == 404
    assert client.get(f"/api/conversions/{job}/profiles/../summary.json").status_code == 404
    assert client.get(f"/api/conversions/{job}/profiles/unknown/preview").status_code == 404


def test_errors_do_not_echo_document_content(client: TestClient, tmp_path: Path):
    path = tmp_path / "secret.docx"
    path.write_bytes(b"PK\x03\x04CONFIDENTIAL-PAYLOAD")
    response = client.post("/api/conversions", files={"file": (path.name, path.read_bytes(), DOCX_TYPE)})
    assert "CONFIDENTIAL" not in response.text


def test_cors_allows_only_configured_origins(client: TestClient):
    allowed = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"
    denied = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in denied.headers
