# Architecture

```
frontend/  Next.js 15 (static export) · TypeScript · Tailwind 4
   │  XHR multipart upload (progress) · fetch JSON/text · iframe preview · download links
   ▼
backend/api/  FastAPI — HTTP shell: limits, rate limiting, job store, headers
   │  spawns
   ▼
backend/api/worker.py  isolated, killable process per conversion
   │  calls
   ▼
backend/knowledge_engine/  pure-Python library, no web dependencies
     validation → readers → document model → profiles → packaging
```

## Conversion engine (`knowledge_engine`)

| Module | Responsibility |
|---|---|
| `validation.py` | Proves an upload is a real, safe OOXML package of the claimed type before any parser runs. |
| `readers/docx_reader.py`, `readers/pptx_reader.py` | Translate Office structure into the model. One class per input format, registered in `readers/__init__.py`. |
| `model.py` | Format-neutral nodes: `Heading`, `Paragraph` (optional callout), `ListBlock`/`ListItem` (nested), `Table` (col/rowspan), `Section` (e.g. a slide with notes); inlines `Text` (bold/italic/underline/strike/sup/sub), `Link`, `ImageRef`, `LineBreak`, `Notice`; plus `Asset`s and stats. |
| `profiles/html_writer.py` | One traversal of the model; `HtmlConventions` let each profile choose markup details (image URLs, alt fallback, callout markup, classes). |
| `profiles/clean.py`, `assets.py`, `freshservice.py` | Output profiles: what files to produce and how they reference each other. |
| `sanitize.py` | nh3 allow-list applied to every generated body. |
| `packaging.py` | ZIP writing with path verification. |
| `pipeline.py` | `convert_to_directory()`: validate → read → render all profiles → write previews, outputs, ZIPs and `summary.json`, with timings. |

### Extending

* **New input format** (e.g. `.odt`, `.md`): add a reader that returns `Document`, register it in `READERS`, and extend `validation.kind_from_name`/`MAIN_CONTENT_TYPES`.
* **New output profile** (e.g. Confluence storage format, Markdown): subclass `OutputProfile`, configure `HtmlWriter` (or write a new writer over the model), and register it in `PROFILES`. The API and UI pick it up from `/api/health` and the conversion summary automatically.

Vendor rules never reach the readers: everything Freshservice-specific is in one profile file.

### Output profiles

| Profile | Primary file | Images | Styling | Package |
|---|---|---|---|---|
| Clean HTML | `document.html` | embedded as data URIs (single portable file) | none, class-free | + `assets/` originals, `manifest.json` |
| HTML + Assets | `index.html` | `assets/images/…` relative | `assets/styles.css` | + `manifest.json` |
| Freshservice Article | `article.html` | `images/…` relative | original inline CSS | + `manifest.json` (original schema), `conversion-report.html` |

Every profile's ZIP is verified in tests so that every `<img src>`/`<link href>` resolves to a file in the package.

## API (`backend/api`)

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Status, limits, profiles |
| `POST /api/conversions` | Multipart `file` → 201 summary (`id`, title, stats, outline, warnings, assets, profiles, timings, `expires_at`) |
| `GET /api/conversions/{id}` | Summary again |
| `GET /api/conversions/{id}/profiles/{profile}/preview` | Self-contained preview HTML, sandboxed by CSP |
| `GET …/profiles/{profile}/source` | Generated HTML as `text/plain` (for the code view) |
| `GET …/profiles/{profile}/html` | Download the HTML |
| `GET …/profiles/{profile}/package` | Download the ZIP |
| `GET /api/conversions/{id}/assets/{file}[?download=1]` | An extracted image |
| `DELETE /api/conversions/{id}` | Delete results immediately |

All conversions render every profile, so switching profile in the UI is instant and needs no re-upload (the upload is already deleted).

Configuration is via `KC_*` environment variables (see `api/config.py` and the README).

## Frontend (`frontend`)

A single client-rendered page: `Intake` (drop zone → real upload progress → server conversion → error states), then `Workspace` (summary, profile switcher, Preview/HTML/Assets views, outline, conversion notes, downloads, expiry). It is a static export, so it deploys to any static host. The API URL comes from `NEXT_PUBLIC_API_BASE_URL` at build time, and `scripts/write-headers.mjs` emits a matching `_headers` CSP.
