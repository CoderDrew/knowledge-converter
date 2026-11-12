# Deployment

The Knowledge Converter is live at **https://converter.mindjax.com**.

## How it is deployed

```
visitor ──HTTPS──▶ Cloudflare Pages      converter.mindjax.com  (static Next.js export)
   │
   └──HTTPS──▶ Caddy (TLS, reverse proxy) api.mindjax.com        DigitalOcean server
                   │
                   ▼
              Docker container           FastAPI API, 1 instance
              ghcr.io/coderdrew/knowledge-converter-api:<commit>
```

The frontend and API live on **different origins** on purpose: generated previews are served by the API origin, so even a sanitiser bypass could not touch the site's origin.

### Frontend: Cloudflare Pages

* Build command: `npm ci && npm run build` (root directory `frontend`)
* Output directory: `out`
* Environment variable: `NEXT_PUBLIC_API_BASE_URL=https://api.mindjax.com`. It is baked in at build time, and `scripts/write-headers.mjs` uses it to write `out/_headers`, the Content-Security-Policy that Pages applies. The live CSP allows `connect-src`, `img-src` and `frame-src` only to `https://api.mindjax.com`.
* Node 20+. No server functions or KV.

### API: Docker on DigitalOcean

* **Image:** `backend/Dockerfile` builds a non-root Python 3.12-slim image. The **Build and Deploy Knowledge Converter API** workflow (`.github/workflows/build-api.yml`, run manually) builds it from the commit it runs on and pushes it to GitHub Container Registry as `ghcr.io/coderdrew/knowledge-converter-api:<short-sha>`.
* **Deploy:** the same workflow connects to the server over SSH with a dedicated deploy key and a pinned host key (`StrictHostKeyChecking=yes`), then runs `sudo -n /usr/local/sbin/mindjax-deploy-knowledge-converter <short-sha>`. That script lives on the server, not in this repository.
* **Secrets** (GitHub Actions): `DEPLOY_SSH_KEY`, `DEPLOY_HOST_KEY`, `DEPLOY_HOST`, `DEPLOY_USER`. Pushing to the registry uses the built-in `GITHUB_TOKEN`.
* **Connectivity check:** the **Test Deployment SSH** workflow (`test-deploy-ssh.yml`) only confirms the SSH connection works.
* **DNS:** `mindjax.com` DNS is on Cloudflare. The `api` record is **DNS-only** (not proxied), so API traffic goes straight to the server and Cloudflare's edge features do not apply to it.
* **Reverse proxy:** Caddy terminates TLS for `api.mindjax.com` and forwards to the container.
* **One instance**, because results and the rate limiter are per-process. Scale with `KC_MAX_CONCURRENT` (isolated conversion subprocesses), not more uvicorn workers or containers.
* Linux is required for the worker's `RLIMIT_AS`/`RLIMIT_CPU` caps to apply.

### What the live API reports

`GET https://api.mindjax.com/api/health` returns the active limits: 20 MB uploads, `.docx`/`.pptx` only, 60 s conversion timeout, 30-minute result lifetime, and the three output profiles. CORS allows only `https://converter.mindjax.com`.

### Environment variables

All API settings are `KC_*` variables (defaults in `backend/api/config.py`).

| Variable | Production value | Purpose |
|---|---|---|
| `KC_ALLOWED_ORIGINS` | `https://converter.mindjax.com` | CORS and preview `frame-ancestors` |
| `KC_MAX_UPLOAD_MB` | `20` | Upload cap (also shown in the UI) |
| `KC_MAX_UNCOMPRESSED_MB` | default `250` | Zip-bomb ceiling |
| `KC_CONVERSION_TIMEOUT_S` | `60` | Worker kill timeout |
| `KC_MAX_CONCURRENT` | default `2` | Parallel isolated workers |
| `KC_QUEUE_WAIT_S` | default `15` | Wait for a slot before 503 |
| `KC_RESULT_TTL_S` | `1800` | Result lifetime |
| `KC_RATE_LIMIT_PER_MINUTE` | default `10` | Conversions per client key per minute (in-process) |
| `KC_MEMORY_LIMIT_MB` | default `1024` | Worker address-space cap (Linux) |
| `KC_TRUST_PROXY_HEADERS` | see below | Read the client IP from `CF-Connecting-IP` / `X-Forwarded-For` |
| `KC_WORK_DIR` | `/tmp/kc-work` (set in the image) | Ephemeral job storage |

Values marked "default" are the code defaults. The values above `/api/health` confirms are the upload cap, timeout and result lifetime.

**`KC_TRUST_PROXY_HEADERS` matters behind Caddy.** With it off, every request appears to come from the proxy, so all visitors share one rate-limit bucket. Turn it on only if the container is reachable solely through Caddy, so clients cannot forge the header.

## Deploying a new version

1. Merge to `main`.
2. In GitHub, run **Build and Deploy Knowledge Converter API** from the Actions tab on `main`.
3. Confirm the deploy: `curl https://api.mindjax.com/api/health`.
4. If frontend code changed, redeploy it on Cloudflare Pages. Its build must keep `NEXT_PUBLIC_API_BASE_URL=https://api.mindjax.com`.

To roll back, redeploy an earlier image: the deploy script takes the image tag as its argument.

## Security in production

* HTTPS on both origins: Cloudflare for the site, Caddy for the API.
* The site's CSP limits network, image and frame access to the API origin. API responses send `default-src 'none'`, `frame-ancestors 'none'`, `nosniff` and `no-referrer`. Previews are served sandboxed from the API origin.
* CORS allows only the site origin.
* Uploads are validated, converted in isolated, time-limited worker processes, and deleted on expiry, on request, and whenever the API starts or stops. See [SECURITY.md](SECURITY.md).
* No Cloudflare WAF or edge rate-limit rules are configured. Rate limiting is the API's in-process limiter.

## Operating cost

There are no databases, queues, paid APIs or persistent storage. Cost is the DigitalOcean server, plus Cloudflare Pages and GitHub Container Registry.

## Before scaling further

* **Fix rate limiting behind the proxy.** Confirm the container is reachable only through Caddy, then set `KC_TRUST_PROXY_HEADERS=true`, so the limiter keys on real client IPs instead of the proxy.
* **Rate-limit at the edge.** Proxy `api.mindjax.com` through Cloudflare, lock the origin to Cloudflare (a Tunnel, or a firewall that allows only Cloudflare IPs), and add a rate-limit rule on `POST /api/conversions` plus a body-size rule matching `KC_MAX_UPLOAD_MB`.
* **Bot protection.** Add Cloudflare Turnstile, checked by the API before it accepts an upload. Not implemented; a small addition to `POST /api/conversions`.
* **Automate and gate deploys.** Run the backend tests and `scripts/check_confidential.py` in the workflow before building the image, and tag images by commit so rollbacks are one command.
* **Monitoring.** Add uptime checks on `/api/health` and alerts for 5xx and 503 (queue full) responses.
* **More than one instance** would need shared state: move results and the rate limiter to shared storage (for example Redis plus object storage) or use sticky routing.
* **Load-test** with large decks to tune `KC_MAX_CONCURRENT`, `KC_MEMORY_LIMIT_MB` and the server size.
