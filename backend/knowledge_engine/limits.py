from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Limits:
    """Resource ceilings applied to every conversion.

    The defaults are sized for a public demo: comfortably above typical job
    aids and decks, far below what would let one upload monopolise a server.
    """

    max_upload_bytes: int = 20 * 1024 * 1024
    max_uncompressed_bytes: int = 250 * 1024 * 1024
    max_archive_entries: int = 5000
    max_compression_ratio: int = 200
    max_assets: int = 400
    max_image_pixels: int = 60_000_000
    max_warnings: int = 100

    def to_dict(self) -> dict[str, int]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> "Limits":
        return cls(**data)
