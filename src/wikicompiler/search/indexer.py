"""Full-text search index builder using Whoosh."""

from __future__ import annotations

from pathlib import Path

from whoosh import index
from whoosh.fields import Schema, TEXT, ID, KEYWORD
from whoosh.qparser import MultifieldParser

from ..vault.frontmatter import read_frontmatter
from ..vault.paths import WIKI_DIR, RAW_DIR
from ..util.logging import info, success

SEARCH_INDEX_DIR = ".search_index"

SCHEMA = Schema(
    path=ID(stored=True, unique=True),
    title=TEXT(stored=True, field_boost=2.0),
    category=KEYWORD(stored=True),
    tags=KEYWORD(stored=True, commas=True),
    summary=TEXT(stored=True),
    body=TEXT(stored=True),
)


def get_index_dir(vault_root: Path) -> Path:
    return vault_root / SEARCH_INDEX_DIR


def build_index(vault_root: Path, include_raw: bool = False) -> int:
    """Build or rebuild the full-text search index.

    Returns the number of documents indexed.
    """
    idx_dir = get_index_dir(vault_root)
    idx_dir.mkdir(parents=True, exist_ok=True)

    ix = index.create_in(str(idx_dir), SCHEMA)
    writer = ix.writer()
    count = 0

    # Index wiki articles
    wiki_dir = vault_root / WIKI_DIR
    if wiki_dir.exists():
        for md_file in wiki_dir.rglob("*.md"):
            if md_file.name.startswith("_"):
                continue
            count += _index_file(writer, vault_root, md_file)

    # Optionally index raw documents
    if include_raw:
        raw_dir = vault_root / RAW_DIR
        if raw_dir.exists():
            for md_file in raw_dir.rglob("*.md"):
                if md_file.name.startswith("_"):
                    continue
                count += _index_file(writer, vault_root, md_file)

    writer.commit()
    success(f"Indexed {count} documents")
    return count


def _index_file(writer, vault_root: Path, md_file: Path) -> int:
    """Index a single markdown file. Returns 1 on success, 0 on failure."""
    try:
        meta, body = read_frontmatter(md_file)
        rel_path = str(md_file.relative_to(vault_root))
        tags = meta.get("tags", [])
        if isinstance(tags, list):
            tags = ",".join(str(t) for t in tags)

        writer.add_document(
            path=rel_path,
            title=meta.get("title", md_file.stem.replace("-", " ").title()),
            category=meta.get("category", ""),
            tags=tags,
            summary=meta.get("summary", ""),
            body=body,
        )
        return 1
    except Exception:
        return 0


def open_index(vault_root: Path):
    """Open the existing search index."""
    idx_dir = get_index_dir(vault_root)
    if not idx_dir.exists() or not index.exists_in(str(idx_dir)):
        # Auto-build if missing
        build_index(vault_root)
    return index.open_dir(str(idx_dir))
