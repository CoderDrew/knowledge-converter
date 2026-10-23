from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from knowledge_engine.limits import Limits


def _int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value not in (None, "") else default


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    return default if value in (None, "") else value.strip().lower() in {"1", "true", "yes", "on"}


def _list(name: str, default: list[str]) -> list[str]:
    value = os.environ.get(name)
    return default if not value else [item.strip().rstrip("/") for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    """Runtime configuration, read from KC_* environment variables."""

    work_dir: Path = field(default_factory=lambda: Path(tempfile.gettempdir()) / "mindjax-knowledge-converter")
    allowed_origins: list[str] = field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])
    max_upload_mb: int = 20
    max_uncompressed_mb: int = 250
    conversion_timeout_s: int = 60
    max_concurrent: int = 2
    queue_wait_s: int = 15
    result_ttl_s: int = 30 * 60
    rate_limit_per_minute: int = 10
    memory_limit_mb: int = 1024
    isolation: str = "process"  # "process" (production) or "inline" (tests only)
    trust_proxy_headers: bool = False

    @property
    def limits(self) -> Limits:
        return Limits(
            max_upload_bytes=self.max_upload_mb * 1024 * 1024,
            max_uncompressed_bytes=self.max_uncompressed_mb * 1024 * 1024,
        )

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        return cls(
            work_dir=Path(os.environ.get("KC_WORK_DIR") or defaults.work_dir),
            allowed_origins=_list("KC_ALLOWED_ORIGINS", defaults.allowed_origins),
            max_upload_mb=_int("KC_MAX_UPLOAD_MB", defaults.max_upload_mb),
            max_uncompressed_mb=_int("KC_MAX_UNCOMPRESSED_MB", defaults.max_uncompressed_mb),
            conversion_timeout_s=_int("KC_CONVERSION_TIMEOUT_S", defaults.conversion_timeout_s),
            max_concurrent=_int("KC_MAX_CONCURRENT", defaults.max_concurrent),
            queue_wait_s=_int("KC_QUEUE_WAIT_S", defaults.queue_wait_s),
            result_ttl_s=_int("KC_RESULT_TTL_S", defaults.result_ttl_s),
            rate_limit_per_minute=_int("KC_RATE_LIMIT_PER_MINUTE", defaults.rate_limit_per_minute),
            memory_limit_mb=_int("KC_MEMORY_LIMIT_MB", defaults.memory_limit_mb),
            isolation=os.environ.get("KC_ISOLATION", defaults.isolation),
            trust_proxy_headers=_bool("KC_TRUST_PROXY_HEADERS", defaults.trust_proxy_headers),
        )
