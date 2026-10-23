# Security and reliability

Each control below is implemented and has an automated test unless marked otherwise. Test files are in `backend/tests/`.

| Threat | Control | Where | Verified by |
|---|---|---|---|
| Wrong or disguised file types | Extension allow-list; ZIP magic; `_rels/.rels` main part; `[Content_Types].xml` main content type must match the extension (clear error on `.pptx` renamed `.docx`) | `knowledge_engine/validation.py` | `test_validation.py` |
| Legacy, encrypted, password-protected files | OLE header and ZIP encryption flag rejected with guidance | `validation.py` | `test_validation.py` |
| Macros / active content | Macro-enabled content types and any `vbaProject.bin` rejected | `validation.py` | `test_validation.py` |
| Corrupted files | Unreadable ZIP/XML → `corrupted`; parser errors mapped to safe messages | `validation.py`, readers | `test_validation.py`, `test_api.py` |
| Oversized uploads | `Content-Length` pre-check plus a streaming byte counter (cuts off chunked/lying clients) plus a post-copy check; default 20 MB (`KC_MAX_UPLOAD_MB`) | `api/guards.py`, `api/main.py` | `test_api.py` (header, streamed and 0 MB cases) |
| Decompression bombs | Total expanded size (250 MB), entry count (5000), per-entry ratio (200× for entries > 10 MB), image pixel cap (60 MP) and asset count (400) | `validation.py`, `readers/common.py` | `test_validation.py` |
| Path traversal / unsafe extraction | Archive members never extracted; names with `..`, absolute, drive, or backslash paths reject the file; all output filenames are engine-generated; package paths re-verified; job IDs are `[0-9a-f]{32}` and resolved under the work root | `validation.py`, `packaging.py`, `api/jobs.py` | `test_validation.py`, `test_api.py` |
| XML external entities | python-docx/pptx parse with `resolve_entities=False`; our own XML reads add `no_network`, no DTD loading | `validation.py` | `test_external_entities_are_not_resolved` |
| Script injection via document text | All text escaped on render; `javascript:` and other non-http(s)/mailto links dropped | `profiles/html_writer.py`, `readers/common.safe_href` | `test_docx_reader.py` |
| Unsafe generated HTML | Every body passes nh3 allow-list sanitisation (no scripts, handlers, styles, iframes, forms, remote images, non-image data URIs) | `knowledge_engine/sanitize.py` | `test_sanitize_and_profiles.py` |
| Preview running in the app's origin | Preview served by the API origin with `Content-Security-Policy: sandbox; default-src 'none'; img-src data:; frame-ancestors <site>`; iframe also has `sandbox=""`; previews are self-contained (no network requests) | `api/main.py`, `PreviewPane.tsx` | `test_api.py`, `test_previews_are_self_contained`; checked in headless Chrome |
| Asset files as attack vectors (e.g. SVG) | Served with `CSP: sandbox; default-src 'none'`, `nosniff`; non-browser formats as attachments | `api/main.py` | `test_api.py` |
| Resource exhaustion / hangs | Each conversion runs in a spawned process, killed after `KC_CONVERSION_TIMEOUT_S` (60 s); on Linux the worker also sets `RLIMIT_AS` (`KC_MEMORY_LIMIT_MB`, 1 GB) and `RLIMIT_CPU`; concurrency semaphore (`KC_MAX_CONCURRENT`, 2) with bounded queue wait → 503 | `api/worker.py`, `api/jobs.py` | `test_isolation.py` (real spawn, timeout kill, crash). RLIMITs are not exercised on Windows. |
| Abuse / floods | In-memory sliding-window limit per client IP (`KC_RATE_LIMIT_PER_MINUTE`, 10) → 429 + `Retry-After` | `api/guards.py` | `test_rate_limit` |
| Temporary files / retention | Unique random job directory; upload deleted immediately after conversion (success or failure); failed jobs removed entirely; results expire after `KC_RESULT_TTL_S` (30 min) via background sweeper; all jobs purged on start and shutdown; user "Delete now" | `api/jobs.py`, `api/main.py` | `test_api.py` |
| Logging of document content | Logs record job id, kind, byte size, duration, error code, and non-content diagnostics (stage, element index, exception type). No filenames or text. | `api/main.py`, `api/worker.py` | `test_errors_do_not_echo_document_content`; manual log review |
| Cross-origin abuse | CORS limited to configured origins; JSON responses carry `frame-ancestors 'none'`, `nosniff`, `no-referrer`, and `no-store` on conversion routes | `api/main.py`, `api/guards.py` | `test_cors_allows_only_configured_origins` |
| Frontend | Static export; `_headers` CSP restricts connect/img/frame sources to the API origin; `object-src 'none'`, `frame-ancestors 'none'` | `frontend/scripts/write-headers.mjs` | Checked in the browser against the production build |

## Before a public deployment

These are planned or partial, and must be in place before the app goes public:

1. **Edge rate limiting.** The in-process limiter only protects one instance. Add a Cloudflare rate-limiting rule on `POST /api/conversions`, and consider Cloudflare Turnstile before upload.
2. **Trusted client IPs.** Behind Cloudflare, set `KC_TRUST_PROXY_HEADERS=true` and make sure the origin accepts traffic **only** from Cloudflare (Cloudflare Tunnel, or a firewall on Cloudflare IP ranges). Otherwise `CF-Connecting-IP` can be spoofed.
3. **Memory limits on the host.** RLIMITs apply on Linux only. Also set container memory limits, since the job store's results occupy disk or `/tmp`.
4. **Single instance or shared storage.** Results live on the instance that produced them, so either run one instance or move results to object storage with signed URLs.
5. **Dependency updates.** Pin and periodically update Python wheels (`pip-audit`) and npm packages (`npm audit` currently reports 0 vulnerabilities, with PostCSS overridden to 8.5.31).
6. **Parser exposure.** Malicious Office files exercise lxml, python-docx, python-pptx and Pillow. Keep them current, and run the worker as an unprivileged user in a minimal container (the Dockerfile does both). Process isolation limits the blast radius but doesn't eliminate it.
