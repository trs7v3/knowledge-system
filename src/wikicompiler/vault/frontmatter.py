"""YAML frontmatter read/write for markdown files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import frontmatter


def read_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    """Read a markdown file and return (metadata_dict, body_content)."""
    post = frontmatter.load(str(path))
    return dict(post.metadata), post.content


def write_frontmatter(path: Path, metadata: dict[str, Any], body: str) -> None:
    """Write a markdown file with YAML frontmatter."""
    post = frontmatter.Post(body, **metadata)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))
        f.write("\n")


def update_frontmatter(path: Path, updates: dict[str, Any]) -> None:
    """Update specific frontmatter fields without touching the body."""
    meta, body = read_frontmatter(path)
    meta.update(updates)
    write_frontmatter(path, meta, body)


def ensure_frontmatter(
    path: Path, defaults: dict[str, Any]
) -> dict[str, Any]:
    """Ensure a file has frontmatter with at least the given default fields.

    Returns the final metadata.
    """
    if path.exists():
        meta, body = read_frontmatter(path)
        changed = False
        for k, v in defaults.items():
            if k not in meta:
                meta[k] = v
                changed = True
        if changed:
            write_frontmatter(path, meta, body)
        return meta
    else:
        write_frontmatter(path, defaults, "")
        return dict(defaults)
