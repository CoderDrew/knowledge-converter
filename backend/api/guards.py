"""Request-level protections: body size cap, rate limiting, security headers."""
from __future__ import annotations

import json
import time
from collections import deque
from typing import Awaitable, Callable

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodyTooLarge(Exception):
    pass


class BodySizeLimitMiddleware:
    """Reject request bodies above `max_bytes` while they stream in.

    Content-Length is checked up front; chunked or lying clients are cut off
    as soon as the running total passes the limit, before the multipart parser
    has spooled the whole upload to disk.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        length = headers.get(b"content-length")
        if length is not None:
            try:
                if int(length) > self.max_bytes:
                    await _reject(send, scope, self.max_bytes)
                    return
            except ValueError:
                await _send_json(send, 400, {"detail": {"code": "bad_request", "message": "Invalid Content-Length header."}})
                return

        received = 0
        started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise BodyTooLarge()
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except BodyTooLarge:
            if not started:
                await _reject(send, scope, self.max_bytes)


async def _reject(send: Send, scope: Scope, max_bytes: int) -> None:
    megabytes = max_bytes // (1024 * 1024)
    await _send_json(send, 413, {"detail": {"code": "file_too_large", "message": f"The upload exceeds the {megabytes} MB limit."}})


async def _send_json(send: Send, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()), (b"connection", b"close")],
    })
    await send({"type": "http.response.body", "body": body})


class RateLimiter:
    """In-memory sliding-window limiter, keyed by client address.

    Adequate for a single-instance demo. A public deployment should also rate
    limit at the edge (e.g. Cloudflare), since in-memory state is per process.
    """

    def __init__(self, limit: int, window_seconds: float = 60.0, max_keys: int = 10_000) -> None:
        self.limit = limit
        self.window = window_seconds
        self.max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}

    def check(self, key: str) -> float | None:
        """Record a hit. Returns seconds to wait if the key is over its limit."""
        if self.limit <= 0:
            return None
        now = time.monotonic()
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return max(1.0, self.window - (now - hits[0]))
        hits.append(now)
        if len(self._hits) > self.max_keys:
            self._prune(now)
        return None

    def _prune(self, now: float) -> None:
        for key in [k for k, v in self._hits.items() if not v or now - v[-1] > self.window]:
            del self._hits[key]


API_CSP = "default-src 'none'; frame-ancestors 'none'"


def security_headers_middleware() -> Callable:
    async def middleware(request, call_next: Callable[..., Awaitable]):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Content-Security-Policy", API_CSP)
        response.headers.setdefault("Cross-Origin-Resource-Policy", "cross-origin")
        if request.url.path.startswith("/api/conversions"):
            response.headers["Cache-Control"] = "no-store"
        return response

    return middleware
