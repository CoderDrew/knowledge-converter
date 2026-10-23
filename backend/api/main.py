"""HTTP API for the Mindjax Knowledge Converter.

The API is a thin shell around `knowledge_engine`: it accepts one upload,
stores it in a private job directory, converts it in an isolated worker,
deletes the upload, and serves the results until they expire.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
import shutil
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.config import Settings
from api.guards import BodySizeLimitMiddleware, BodyTooLarge, RateLimiter, security_headers_middleware
from api.jobs import Job, JobStore, run_conversion
from knowledge_engine import __version__
from knowledge_engine.errors import ConversionError
from knowledge_engine.profiles import PROFILES
from knowledge_engine.validation import kind_from_name


log = logging.getLogger("knowledge_converter")
MULTIPART_OVERHEAD = 1024 * 1024
COPY_CHUNK = 1024 * 1024
ASSET_NAME = re.compile(r"^[a-z0-9-]+\.[a-z0-9]+$")


def _error(status: int, code: str, message: str, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse({"detail": {"code": code, "message": message}}, status_code=status, headers=headers)


def _caused_by(exc: BaseException, kind: type[BaseException]) -> bool:
    if isinstance(exc, kind):
        return True
    if isinstance(exc, BaseExceptionGroup):
        return any(_caused_by(inner, kind) for inner in exc.exceptions)
    return exc.__cause__ is not None and _caused_by(exc.__cause__, kind)


def _display_name(filename: str) -> str:
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C").strip()
    return name[:180] or "document"


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")[:60] or "document"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = JobStore(settings.work_dir, settings.result_ttl_s)
    limiter = RateLimiter(settings.rate_limit_per_minute)
    slots = asyncio.Semaphore(settings.max_concurrent)
    frame_ancestors = " ".join(settings.allowed_origins) or "'none'"
    preview_csp = (
        "default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; "
        f"frame-ancestors {frame_ancestors}; sandbox"
    )

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI):
        store.purge_all()  # results never outlive the process that produced them

        async def sweeper() -> None:
            while True:
                await asyncio.sleep(60)
                with contextlib.suppress(Exception):
                    removed = await asyncio.to_thread(store.sweep)
                    if removed:
                        log.info("expired %d conversion workspace(s)", removed)

        task = asyncio.create_task(sweeper())
        try:
            yield
        finally:
            task.cancel()
            store.purge_all()

    app = FastAPI(title="Mindjax Knowledge Converter API", version=__version__, docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.settings = settings
    app.state.store = store
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
        expose_headers=["Content-Disposition"],
        max_age=600,
    )
    app.middleware("http")(security_headers_middleware())
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.limits.max_upload_bytes + MULTIPART_OVERHEAD)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "error")
        return _error(exc.status_code, code, str(exc.detail))

    def client_key(request: Request) -> str:
        if settings.trust_proxy_headers:
            forwarded = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            if forwarded:
                return forwarded
        return request.client.host if request.client else "unknown"

    def job_or_404(job_id: str) -> Job:
        job = store.get(job_id)
        if job is None:
            raise StarletteHTTPException(404, "This conversion has expired or does not exist.")
        return job

    def summary_for(job: Job) -> dict:
        summary = json.loads((job.out_dir / "summary.json").read_text(encoding="utf-8"))
        expires = store.created_at(job) + settings.result_ttl_s
        summary["id"] = job.id
        summary["expires_at"] = datetime.fromtimestamp(expires, timezone.utc).isoformat()
        return summary

    def profile_dir(job: Job, profile_id: str) -> Path:
        if profile_id not in PROFILES:
            raise StarletteHTTPException(404, "Unknown output profile.")
        return job.out_dir / "profiles" / profile_id

    def download_name(job: Job, profile_id: str, suffix: str) -> str:
        summary = json.loads((job.out_dir / "summary.json").read_text(encoding="utf-8"))
        return f"{_slug(Path(summary['source']['name']).stem)}-{profile_id}.{suffix}"

    # ---------------------------------------------------------------- routes

    @app.get("/api/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "version": __version__,
            "limits": {
                "max_upload_bytes": settings.limits.max_upload_bytes,
                "accepted_extensions": [".docx", ".pptx"],
                "result_ttl_seconds": settings.result_ttl_s,
                "conversion_timeout_seconds": settings.conversion_timeout_s,
            },
            "profiles": [profile.describe() for profile in PROFILES.values()],
        }

    @app.post("/api/conversions", status_code=201)
    async def create_conversion(request: Request):
        wait = limiter.check(client_key(request))
        if wait is not None:
            return _error(429, "rate_limited", "Too many conversions in a short time. Please wait a moment and try again.", {"Retry-After": str(int(wait))})

        try:
            form = await request.form(max_files=1, max_fields=4)
        except Exception as exc:
            if _caused_by(exc, BodyTooLarge):
                return _error(413, "file_too_large", f"The upload exceeds the {settings.max_upload_mb} MB limit.")
            return _error(400, "bad_request", 'The upload could not be read. Send one file as multipart form data in a field named "file".')
        started = time.perf_counter()
        job: Job | None = None
        try:
            upload = form.get("file")
            if not isinstance(upload, UploadFile) or not upload.filename:
                return _error(400, "missing_file", "Choose a .docx or .pptx file to convert.")
            name = _display_name(upload.filename)
            try:
                kind = kind_from_name(name)
            except ConversionError as exc:
                return _error(exc.status, exc.code, exc.message)

            try:
                await asyncio.wait_for(slots.acquire(), timeout=settings.queue_wait_s)
            except asyncio.TimeoutError:
                return _error(503, "server_busy", "The converter is busy right now. Please try again in a few seconds.", {"Retry-After": "10"})
            try:
                job = store.create()
                source = job.upload_dir / f"source.{kind}"
                size = 0
                with source.open("wb") as target:
                    while chunk := await upload.read(COPY_CHUNK):
                        size += len(chunk)
                        if size > settings.limits.max_upload_bytes:
                            return _error(413, "file_too_large", f"The file exceeds the {settings.max_upload_mb} MB upload limit.")
                        target.write(chunk)
                await form.close()
                try:
                    await asyncio.to_thread(run_conversion, settings, source, name, job.out_dir)
                finally:
                    shutil.rmtree(job.upload_dir, ignore_errors=True)
            finally:
                slots.release()

            elapsed = round((time.perf_counter() - started) * 1000)
            log.info("conversion ok job=%s kind=%s bytes=%d ms=%d", job.id, kind, size, elapsed)
            result = summary_for(job)
            job = None  # keep results
            return JSONResponse(result, status_code=201)
        except ConversionError as exc:
            diagnostic = getattr(exc, "diagnostic", {}) or {}
            log.warning("conversion failed code=%s status=%d diagnostic=%s", exc.code, exc.status, json.dumps(diagnostic))
            return _error(exc.status, exc.code, exc.message)
        finally:
            await form.close()
            if job is not None:
                store.discard(job)

    @app.get("/api/conversions/{job_id}")
    async def get_conversion(job_id: str) -> dict:
        return summary_for(job_or_404(job_id))

    @app.delete("/api/conversions/{job_id}", status_code=204)
    async def delete_conversion(job_id: str) -> Response:
        store.delete(job_id)
        return Response(status_code=204)

    @app.get("/api/conversions/{job_id}/profiles/{profile_id}/preview")
    async def preview(job_id: str, profile_id: str) -> Response:
        path = profile_dir(job_or_404(job_id), profile_id) / "preview.html"
        return Response(
            path.read_bytes(),
            media_type="text/html; charset=utf-8",
            headers={"Content-Security-Policy": preview_csp},
        )

    @app.get("/api/conversions/{job_id}/profiles/{profile_id}/source")
    async def source(job_id: str, profile_id: str) -> Response:
        path = profile_dir(job_or_404(job_id), profile_id) / "output.html"
        return Response(path.read_bytes(), media_type="text/plain; charset=utf-8")

    @app.get("/api/conversions/{job_id}/profiles/{profile_id}/html")
    async def download_html(job_id: str, profile_id: str) -> FileResponse:
        job = job_or_404(job_id)
        path = profile_dir(job, profile_id) / "output.html"
        return FileResponse(
            path,
            media_type="text/html; charset=utf-8",
            filename=download_name(job, profile_id, "html"),
            headers={"Content-Security-Policy": "default-src 'none'; sandbox"},
        )

    @app.get("/api/conversions/{job_id}/profiles/{profile_id}/package")
    async def download_package(job_id: str, profile_id: str) -> FileResponse:
        job = job_or_404(job_id)
        path = profile_dir(job, profile_id) / "package.zip"
        return FileResponse(path, media_type="application/zip", filename=download_name(job, profile_id, "zip"))

    @app.get("/api/conversions/{job_id}/assets/{filename}")
    async def asset(job_id: str, filename: str, download: bool = False) -> FileResponse:
        job = job_or_404(job_id)
        if not ASSET_NAME.match(filename):
            raise StarletteHTTPException(404, "Asset not found.")
        meta = next((a for a in summary_for(job)["assets"] if a["filename"] == filename), None)
        path = job.out_dir / "assets" / filename
        if meta is None or not path.is_file():
            raise StarletteHTTPException(404, "Asset not found.")
        return FileResponse(
            path,
            media_type=meta["content_type"] if meta["displayable"] else "application/octet-stream",
            filename=filename,
            content_disposition_type="inline" if meta["displayable"] and not download else "attachment",
            headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox"},
        )

    return app


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
app = create_app()
