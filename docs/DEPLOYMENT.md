# Deployment plan

Nothing in this document has been provisioned. It describes what a public demo deployment needs.

## Target shape

```
visitor ──HTTPS──▶ Cloudflare Pages   lab.mindjax.com/knowledge-converter (static export)
   │
   └──HTTPS──▶ Cloudflare proxy (WAF, rate limit, optional Turnstile)
                   │  Tunnel or IP-allow-listed origin
                   ▼
              Python container       api.converter.mindjax.com (FastAPI, 1 instance)
```

The frontend and API live on **different origins** on purpose: generated previews are served by the API origin, so even a sanitiser bypass could not touch the site's origin.

## Frontend: Cloudflare Pages

* Build command: `npm ci && npm run build` (root directory `frontend`)
* Output directory: `out`
* Environment variable: `NEXT_PUBLIC_API_BASE_URL=https://api.converter.mindjax.com` (baked in at build time; `scripts/write-headers.mjs` also uses it to write `out/_headers`, the CSP for Pages)
* Node 20+. No server functions or KV are needed. If the site is mounted under a sub-path of mindjax.com, set Next.js `basePath` accordingly.

## API: any Python/container host

Requirements:

* Python 3.11+ (container uses 3.12-slim), **Linux recommended** (enables the worker's `RLIMIT_AS`/`RLIMIT_CPU` caps)
* 1 vCPU / 1–2 GB RAM is ample for `KC_MAX_CONCURRENT=2`
* Writable ephemeral disk for `KC_WORK_DIR` (results are short-lived; no persistent volume needed)
* **One instance** (or sticky routing), because results and the rate limiter are per-process
* Ability to spawn subprocesses (most container platforms allow this)

`backend/Dockerfile` builds a non-root image. It was written but **not yet built**: Docker Desktop's engine wasn't running during development. Build and smoke-test it before the first deployment:

```bash
docker build -t knowledge-converter-api backend
docker run --rm -p 8000:8000 -e KC_ALLOWED_ORIGINS=http://localhost:3000 knowledge-converter-api
```

Suitable low-cost hosts (pick one):

| Host | Notes | Rough cost for a demo |
|---|---|---|
| Fly.io Machines | Runs the Dockerfile as-is; scale-to-zero with auto-start; pin to 1 machine | ~$0–5/month |
| Google Cloud Run | `--max-instances=1`, `--memory=2Gi`, `--timeout=120`; `/tmp` is in-memory, so budget RAM for results | Free tier usually covers demo traffic |
| Render / Railway | Docker web service, 1 instance | ~$7/month |
| Small VPS + Cloudflare Tunnel | Most control; no inbound ports | ~$5/month |

### Production environment variables

| Variable | Recommended | Purpose |
|---|---|---|
| `KC_ALLOWED_ORIGINS` | `https://lab.mindjax.com` | CORS and preview `frame-ancestors` |
| `KC_MAX_UPLOAD_MB` | `20` | Upload cap (also shown in the UI) |
| `KC_MAX_UNCOMPRESSED_MB` | `250` | Zip-bomb ceiling |
| `KC_CONVERSION_TIMEOUT_S` | `60` | Worker kill timeout |
| `KC_MAX_CONCURRENT` | `2` | Parallel isolated workers |
| `KC_QUEUE_WAIT_S` | `15` | Wait for a slot before 503 |
| `KC_RESULT_TTL_S` | `1800` | Result lifetime |
| `KC_RATE_LIMIT_PER_MINUTE` | `6`–`10` | Per-IP conversions (in-process) |
| `KC_MEMORY_LIMIT_MB` | `1024` | Worker address-space cap (Linux) |
| `KC_TRUST_PROXY_HEADERS` | `true` **only** behind Cloudflare with origin locked down | Use `CF-Connecting-IP` for rate limiting |
| `KC_WORK_DIR` | `/tmp/kc-work` | Ephemeral job storage |

## Secure communication

* HTTPS everywhere (Pages and the Cloudflare proxy terminate TLS; use Full (strict) to the origin, or a Tunnel).
* CORS allows only the Pages origin; the preview `frame-ancestors` is derived from the same list.
* Lock the origin to Cloudflare (Tunnel preferred) so the edge rate limit and WAF can't be bypassed.
* Add a Cloudflare rate-limiting rule on `POST /api/conversions` (e.g. 10/min/IP) and a body-size rule matching `KC_MAX_UPLOAD_MB`.
* Optional: Cloudflare Turnstile token checked by the API before accepting an upload. It isn't implemented; it would be a small addition to `POST /api/conversions`.

## Operating cost

With scale-to-zero hosting, cost is dominated by the API's idle policy: roughly $0–10/month for demo traffic. There are no databases, queues, paid APIs, or persistent storage.

## Pre-launch checklist

- [ ] Build and run the Docker image; run `scripts/compare_with_original.py` and the test suite in CI
- [ ] Set production env vars; confirm `/api/health` limits
- [ ] Confirm CSP headers on Pages (`curl -I`) and the API preview (`sandbox` present)
- [ ] Origin reachable only via Cloudflare; edge rate limit active
- [ ] Replace the placeholder Mindjax mark with the official logo, and review copy
- [ ] Load-test with a few large decks to tune `KC_MAX_CONCURRENT` and memory
