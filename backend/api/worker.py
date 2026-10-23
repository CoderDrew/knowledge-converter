"""Conversion worker, executed in a separate, killable process.

Running untrusted documents out-of-process means a pathological file can only
exhaust its own worker: the parent enforces a wall-clock timeout by killing
it, and on POSIX hosts the worker also caps its own address space and CPU
time. The outcome is written to a JSON file; exceptions never carry document
content back to the API.
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path


def _apply_resource_limits(memory_mb: int, cpu_seconds: int) -> None:
    if sys.platform == "win32":
        return  # Wall-clock timeout in the parent still applies.
    import resource

    if memory_mb > 0:
        limit = memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    if cpu_seconds > 0:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 5))


def run(source: str, source_name: str, out_dir: str, limits: dict, outcome_path: str, memory_mb: int = 0, cpu_seconds: int = 0) -> None:
    _apply_resource_limits(memory_mb, cpu_seconds)
    outcome: dict
    try:
        from knowledge_engine.errors import ConversionError
        from knowledge_engine.limits import Limits
        from knowledge_engine.pipeline import convert_to_directory

        try:
            convert_to_directory(Path(source), source_name, Path(out_dir), Limits.from_dict(limits))
            outcome = {"ok": True}
        except ConversionError as exc:
            context = exc.diagnostic_context() if hasattr(exc, "diagnostic_context") else {}
            cause = exc.__cause__
            if cause is not None:
                context["exception_type"] = type(cause).__name__
            outcome = {"ok": False, "status": exc.status, "error": exc.to_dict(), "diagnostic": context}
    except MemoryError:
        outcome = {"ok": False, "status": 422, "error": {"code": "resource_limit", "message": "The document needs more memory than this service allows."}}
    except Exception as exc:  # noqa: BLE001 - last-resort boundary
        # The stack trace references engine code only; document text is not
        # interpolated into engine exception messages.
        frames = traceback.extract_tb(exc.__traceback__)
        where = f"{Path(frames[-1].filename).name}:{frames[-1].lineno}" if frames else None
        outcome = {
            "ok": False,
            "status": 422,
            "error": {"code": "conversion_failed", "message": "The document could not be converted."},
            "diagnostic": {"exception_type": type(exc).__name__, "location": where},
        }
    Path(outcome_path).write_text(json.dumps(outcome), encoding="utf-8")
