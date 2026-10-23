from __future__ import annotations


class ConversionError(Exception):
    """A failure that is safe to show to the person who uploaded the file.

    `code` is stable and machine-readable; `message` never includes document
    content. `status` is the HTTP status an API layer should use.
    """

    status = 422

    def __init__(self, code: str, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        if status is not None:
            self.status = status

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


class UnsupportedFileError(ConversionError):
    status = 415


class InvalidDocumentError(ConversionError):
    status = 422


class LimitExceededError(ConversionError):
    status = 413
