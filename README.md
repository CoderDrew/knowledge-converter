# Mindjax Knowledge Converter

Turn Word (.docx) and PowerPoint (.pptx) files into clean, publish-ready HTML, with every embedded image extracted and a portable export package, in a few seconds. A Mindjax Innovation Lab project.

* **Engine** (`backend/knowledge_engine`): a standalone Python library. It validates Office packages, reads them into a format-neutral document model, and renders output profiles.
* **API** (`backend/api`): FastAPI. Isolated, time-limited conversion workers; upload limits; rate limiting; automatic deletion.
* **Web app** (`frontend`): Next.js + TypeScript + Tailwind, exported as a static site.

Docs: [Audit of the original app](docs/AUDIT.md) · [Architecture](docs/ARCHITECTURE.md) · [Security](docs/SECURITY.md) · [Deployment plan](docs/DEPLOYMENT.md)

## Run locally

Prerequisites: Python 3.11+, Node.js 20+.

Quick start on Windows (sets up both halves on first run):

```powershell
.\run.ps1
```

Or run each part yourself:

```bash
# API: http://127.0.0.1:8000
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt     # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

```bash
# Web app: http://localhost:3000
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

Open http://localhost:3000, drop a `.docx` or `.pptx`, then use **Preview**, **HTML**, and **Assets**, switch **Output profile**, and download the HTML or ZIP. Synthetic samples are in `backend/samples/`.

Production-style check of the static export, with the real CSP headers applied:

```bash
cd frontend && npm run build && npm start
```

## Output profiles

| Profile | You get |
|---|---|
| **Clean HTML** | `document.html`: semantic, class-free markup with images embedded, in one portable file. The ZIP adds original images and a manifest. |
| **HTML + Assets** | `index.html` + `assets/styles.css` + `assets/images/…` with relative references, plus a manifest. Drop it on any static host. |
| **Freshservice Article** | The original FS Knowledge Converter's contract: `article.html`, `images/`, `manifest.json` (nearest heading/step), `conversion-report.html`. |

## What converts

**Word:** headings (including Title), paragraphs, bold/italic/underline/strike/super/subscript, hyperlinks (http/https/mailto only), nested bulleted and numbered lists (with recovery from broken numbering and continuation across image-only paragraphs), tables with merged cells, note/tip/warning/caution callouts, inline images (DrawingML and legacy VML) with authored alt text, content controls, and tracked changes (insertions kept, deletions dropped).

**PowerPoint:** each slide becomes a `<section>` with its title (title placeholder, or the most prominent text near the top for text-box-only decks), text in visual reading order, bulleted/numbered lists with levels, tables with merged cells, pictures (including inside groups), and speaker notes.

**Flagged rather than converted** (shown as conversion notes in the UI): charts, SmartArt, text boxes in Word, footnotes, embedded media/OLE objects, linked images, and EMF/WMF images (kept in the package, shown as placeholders).

## Tests

```bash
cd backend
.venv/Scripts/python -m pytest
```

97 tests cover DOCX/PPTX semantics, images, tables and lists, formatting, HTML generation, sanitisation, ZIP integrity (every reference resolves), invalid/corrupted/disguised/macro/encrypted files, zip bombs, path traversal, XXE, oversized and streamed uploads, rate limiting, temp-file cleanup and expiry, preview CSP headers, and process isolation (a real spawned worker, timeout kill, crash).

Regression check against the original application (read-only import of its converter):

```bash
cd backend
.venv/Scripts/python scripts/compare_with_original.py "C:/Projects/FS Knowledge Converter" "samples/Sample Cash Management.docx"
```

Frontend type-check: `cd frontend && npm run lint`.

## Configuration

API settings are `KC_*` environment variables. Defaults: 20 MB uploads, 60 s timeout, 2 concurrent workers, 30-minute result lifetime, 10 conversions/minute per IP, CORS for `localhost:3000`. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#production-environment-variables) for the full list.

The web app reads `NEXT_PUBLIC_API_BASE_URL` (default `http://127.0.0.1:8000`).

## Notes

* The header mark is a placeholder; swap in the official Mindjax logo before showcasing.
* Results are kept only in a temporary directory and are deleted on expiry, on request, and whenever the API starts or stops.
