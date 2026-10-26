"""Pre-render the synthetic samples into static files for the web app's demo mode.

Runs the real API in-process (no network, no paid services) and writes
frontend/public/demo/<slug>/... so a static host can serve a working demo
without a backend. Only the synthetic files in backend/samples/ are used
for input (regenerate those with scripts/generate_samples.py).

    cd backend && .venv/bin/python scripts/build_demo_fixtures.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

from api.main import create_app  # noqa: E402

SAMPLES = {
    "sample-docx": "sample-expense-guide.docx",
    "sample-pptx": "sample-expense-guide.pptx",
}
OUT = BACKEND.parent / "frontend" / "public" / "demo"


def main() -> None:
    shutil.rmtree(OUT, ignore_errors=True)
    client = TestClient(create_app())
    index = []
    for slug, name in SAMPLES.items():
        path = BACKEND / "samples" / name
        with path.open("rb") as fh:
            r = client.post("/api/conversions", files={"file": (name, fh)})
        r.raise_for_status()
        conv = r.json()
        job = conv["id"]
        conv["id"] = slug
        conv["expires_at"] = "2099-01-01T00:00:00Z"
        base = OUT / slug
        for profile in conv["profiles"]:
            pid = profile["id"]
            pdir = base / "profiles" / pid
            pdir.mkdir(parents=True, exist_ok=True)
            for route, fname in (("preview", "preview.html"), ("source", "source.txt"), ("html", "output.html"), ("package", "package.zip")):
                resp = client.get(f"/api/conversions/{job}/profiles/{pid}/{route}")
                resp.raise_for_status()
                (pdir / fname).write_bytes(resp.content)
        adir = base / "assets"
        adir.mkdir(parents=True, exist_ok=True)
        for asset in conv["assets"]:
            resp = client.get(f"/api/conversions/{job}/assets/{asset['filename']}")
            resp.raise_for_status()
            (adir / asset["filename"]).write_bytes(resp.content)
        (base / "conversion.json").write_text(json.dumps(conv, indent=1), encoding="utf-8")
        client.delete(f"/api/conversions/{job}")
        index.append({"id": slug, "name": name, "kind": conv["source"]["kind"], "title": conv["title"]})
        print(f"{slug}: {len(conv['assets'])} assets, {len(conv['profiles'])} profiles")
    health = client.get("/api/health").json()
    (OUT / "index.json").write_text(json.dumps({"samples": index, "health": health}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
