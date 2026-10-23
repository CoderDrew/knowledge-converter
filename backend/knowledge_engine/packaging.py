from __future__ import annotations

import re
import zipfile
from pathlib import Path


_SAFE_MEMBER = re.compile(r"^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*$")


def write_zip(files: dict[str, bytes], destination: Path) -> int:
    """Write an export package. Member names are engine-generated; verify anyway."""
    for name in files:
        if not _SAFE_MEMBER.match(name) or ".." in name.split("/"):
            raise ValueError(f"Refusing unsafe package path: {name!r}")
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in sorted(files, key=lambda n: (n.count("/"), n)):
            archive.writestr(name, files[name])
    return destination.stat().st_size
