"""Content hashing for change detection."""

from __future__ import annotations

import hashlib
from pathlib import Path


def hash_content(content: str) -> str:
    """Return SHA-256 hex digest of string content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def hash_file(path: Path) -> str:
    """Return SHA-256 hex digest of a file's contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
