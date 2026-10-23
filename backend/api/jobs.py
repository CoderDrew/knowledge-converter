"""Short-lived conversion workspaces and the isolated conversion runner."""
from __future__ import annotations

import json
import multiprocessing
import re
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from api import worker
from api.config import Settings
from knowledge_engine.errors import ConversionError


JOB_ID = re.compile(r"^[0-9a-f]{32}$")


@dataclass
class Job:
    id: str
    root: Path

    @property
    def upload_dir(self) -> Path:
        return self.root / "upload"

    @property
    def out_dir(self) -> Path:
        return self.root / "out"


class JobStore:
    """Each conversion gets a private directory named by a random 128-bit id.

    The id doubles as the capability to fetch results, so it is never derived
    from the filename. Directories are removed when their TTL expires, when
    the user discards them, and on every server start.
    """

    def __init__(self, root: Path, ttl_seconds: int) -> None:
        self.root = root
        self.ttl = ttl_seconds
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self) -> Job:
        job_id = uuid.uuid4().hex
        job = Job(job_id, self.root / job_id)
        job.upload_dir.mkdir(parents=True)
        job.out_dir.mkdir()
        (job.root / "meta.json").write_text(json.dumps({"created": time.time()}), encoding="utf-8")
        return job

    def get(self, job_id: str) -> Job | None:
        if not JOB_ID.match(job_id):
            return None
        root = (self.root / job_id).resolve()
        if root.parent != self.root.resolve() or not (root / "out" / "summary.json").is_file():
            return None
        if self._expired(root):
            self.delete(job_id)
            return None
        return Job(job_id, root)

    def created_at(self, job: Job) -> float:
        try:
            return float(json.loads((job.root / "meta.json").read_text(encoding="utf-8"))["created"])
        except (OSError, ValueError, KeyError):
            return job.root.stat().st_mtime

    def _expired(self, root: Path) -> bool:
        try:
            created = float(json.loads((root / "meta.json").read_text(encoding="utf-8"))["created"])
        except (OSError, ValueError, KeyError):
            created = root.stat().st_mtime if root.exists() else 0
        return time.time() - created > self.ttl

    def delete(self, job_id: str) -> bool:
        if not JOB_ID.match(job_id):
            return False
        root = self.root / job_id
        existed = root.exists()
        shutil.rmtree(root, ignore_errors=True)
        return existed

    def discard(self, job: Job) -> None:
        shutil.rmtree(job.root, ignore_errors=True)

    def sweep(self) -> int:
        removed = 0
        for child in self.root.iterdir():
            if child.is_dir() and JOB_ID.match(child.name) and self._expired(child):
                shutil.rmtree(child, ignore_errors=True)
                removed += 1
        return removed

    def purge_all(self) -> None:
        for child in self.root.iterdir():
            if child.is_dir() and JOB_ID.match(child.name):
                shutil.rmtree(child, ignore_errors=True)


def run_conversion(settings: Settings, source: Path, source_name: str, out_dir: Path, target: Callable = worker.run) -> None:
    """Convert in an isolated process (or inline for tests). Raises ConversionError."""
    limits = settings.limits.to_dict()
    outcome_path = out_dir.parent / "outcome.json"
    if settings.isolation == "inline":
        target(str(source), source_name, str(out_dir), limits, str(outcome_path))
    else:
        context = multiprocessing.get_context("spawn")
        process = context.Process(
            target=target,
            args=(str(source), source_name, str(out_dir), limits, str(outcome_path), settings.memory_limit_mb, settings.conversion_timeout_s),
            daemon=True,
        )
        process.start()
        process.join(settings.conversion_timeout_s)
        if process.is_alive():
            process.kill()
            process.join(5)
            raise ConversionError(
                "processing_timeout",
                f"Conversion took longer than {settings.conversion_timeout_s} seconds and was stopped. Try a smaller document.",
            )
        if process.exitcode != 0 and not outcome_path.exists():
            raise ConversionError("resource_limit", "The conversion worker stopped unexpectedly, likely because the document exceeded resource limits.")
    try:
        outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ConversionError("conversion_failed", "The document could not be converted.") from None
    finally:
        outcome_path.unlink(missing_ok=True)
    if not outcome.get("ok"):
        error = outcome.get("error", {})
        exc = ConversionError(error.get("code", "conversion_failed"), error.get("message", "The document could not be converted."), status=outcome.get("status", 422))
        exc.diagnostic = outcome.get("diagnostic") or {}  # type: ignore[attr-defined]
        raise exc
