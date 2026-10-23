"""Process isolation: real spawned workers, a real timeout, and a crash."""
import dataclasses
import os
import time
from pathlib import Path

import pytest

from api.config import Settings
from api.jobs import JobStore, run_conversion
from knowledge_engine.errors import ConversionError


def slow_worker(*_args, **_kwargs) -> None:
    time.sleep(30)


def crashing_worker(*_args, **_kwargs) -> None:
    os._exit(3)


@pytest.fixture
def process_settings(settings: Settings) -> Settings:
    return dataclasses.replace(settings, isolation="process", conversion_timeout_s=20)


def test_conversion_succeeds_in_a_separate_process(process_settings: Settings, sample_docx: Path):
    job = JobStore(process_settings.work_dir, 60).create()
    run_conversion(process_settings, sample_docx, sample_docx.name, job.out_dir)
    assert (job.out_dir / "summary.json").is_file()


def test_worker_is_killed_after_timeout(process_settings: Settings, sample_docx: Path):
    fast = dataclasses.replace(process_settings, conversion_timeout_s=3)
    job = JobStore(fast.work_dir, 60).create()
    started = time.monotonic()
    with pytest.raises(ConversionError) as raised:
        run_conversion(fast, sample_docx, sample_docx.name, job.out_dir, target=slow_worker)
    assert raised.value.code == "processing_timeout"
    assert time.monotonic() - started < 15


def test_worker_crash_is_reported(process_settings: Settings, sample_docx: Path):
    job = JobStore(process_settings.work_dir, 60).create()
    with pytest.raises(ConversionError) as raised:
        run_conversion(process_settings, sample_docx, sample_docx.name, job.out_dir, target=crashing_worker)
    assert raised.value.code == "resource_limit"


def test_engine_failure_inside_worker_is_contained(process_settings: Settings, tmp_path: Path):
    bogus = tmp_path / "bogus.docx"; bogus.write_bytes(b"PK\x03\x04nope")
    job = JobStore(process_settings.work_dir, 60).create()
    with pytest.raises(ConversionError) as raised:
        run_conversion(process_settings, bogus, bogus.name, job.out_dir)
    assert raised.value.code == "corrupted"
