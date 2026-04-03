"""Vault path conventions, layout constants, and safe file operations."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Default vault subdirectories
RAW_DIR = "raw"
WIKI_DIR = "wiki"
OUTPUT_DIR = "output"
ASSETS_DIR = "assets"

# Raw subdirectories
RAW_ARTICLES = f"{RAW_DIR}/articles"
RAW_PAPERS = f"{RAW_DIR}/papers"
RAW_REPOS = f"{RAW_DIR}/repos"
RAW_IMAGES = f"{RAW_DIR}/images"

# Wiki categories
WIKI_CATEGORIES = ["concepts", "entities", "techniques", "references"]

# Index / manifest files
RAW_INDEX = f"{RAW_DIR}/_index.md"
WIKI_INDEX = f"{WIKI_DIR}/_index.md"
WIKI_SUMMARIES = f"{WIKI_DIR}/_summaries.md"
COMPILATION_STATE = f"{WIKI_DIR}/_compilation_state.yaml"

# Obsidian config
OBSIDIAN_DIR = ".obsidian"


def resolve_vault(vault_path: str | Path | None = None) -> Path:
    """Resolve the vault root directory.

    Searches upward from CWD for a directory containing .wiki.toml,
    or uses the given path.
    """
    if vault_path:
        return Path(vault_path).resolve()

    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".wiki.toml").exists():
            return parent
        if (parent / "vault").is_dir() and (parent / "vault" / ".wiki.toml").exists():
            return parent / "vault"

    return current / "vault"


def ensure_within_vault(vault_root: Path, target: Path) -> Path:
    """Validate that target path is within the vault. Raises ValueError if not.

    Uses Path.relative_to() for safe containment checking — immune to
    prefix-based bypasses like /vault vs /vault-evil.
    """
    resolved = target.resolve()
    vault_resolved = vault_root.resolve()
    try:
        resolved.relative_to(vault_resolved)
    except ValueError:
        raise ValueError(
            f"Path {resolved} is outside vault root {vault_resolved}"
        )
    return resolved


def safe_write(vault_root: Path, rel_path: str, content: str) -> Path:
    """Atomically write content to a file within the vault.

    Writes to a temp file first, then renames for crash safety.
    Creates parent directories as needed.
    """
    target = vault_root / rel_path
    ensure_within_vault(vault_root, target)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=target.parent, suffix=".tmp", prefix=".wiki_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, target)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return target


def safe_read(vault_root: Path, rel_path: str) -> str:
    """Read a file from within the vault."""
    target = vault_root / rel_path
    ensure_within_vault(vault_root, target)
    return target.read_text(encoding="utf-8")


def slug(text: str) -> str:
    """Convert text to a kebab-case slug suitable for filenames."""
    import re

    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def init_vault_dirs(vault_root: Path) -> None:
    """Create the standard vault directory structure."""
    dirs = [
        RAW_ARTICLES,
        RAW_PAPERS,
        RAW_REPOS,
        RAW_IMAGES,
        *[f"{WIKI_DIR}/{cat}" for cat in WIKI_CATEGORIES],
        OUTPUT_DIR,
        ASSETS_DIR,
        OBSIDIAN_DIR,
    ]
    for d in dirs:
        (vault_root / d).mkdir(parents=True, exist_ok=True)
