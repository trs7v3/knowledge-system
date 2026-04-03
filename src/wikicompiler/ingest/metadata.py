"""Metadata extraction and raw document manifest maintenance."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ..vault.frontmatter import read_frontmatter, write_frontmatter
from ..vault.paths import RAW_INDEX
from ..util.hashing import hash_content


def create_raw_metadata(
    source_type: str,
    title: str,
    content: str,
    source_url: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Create frontmatter metadata for a raw document."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "title": title,
        "source_type": source_type,
        "source_url": source_url or "",
        "ingested_at": now,
        "content_hash": hash_content(content),
        "tags": tags or ["raw", "unprocessed"],
        "status": "unprocessed",
    }


def update_raw_index(vault_root: Path, doc_path: str, metadata: dict[str, Any]) -> None:
    """Add or update a document entry in the raw index manifest."""
    index_path = vault_root / RAW_INDEX

    if index_path.exists():
        meta, body = read_frontmatter(index_path)
    else:
        meta = {"type": "raw_index", "documents": [], "document_count": 0}
        body = "# Raw Documents Index\n"

    docs = meta.get("documents", [])

    # Check if doc already exists
    existing = None
    for i, doc in enumerate(docs):
        if doc.get("path") == doc_path:
            existing = i
            break

    entry = {
        "path": doc_path,
        "title": metadata.get("title", ""),
        "source_type": metadata.get("source_type", ""),
        "content_hash": metadata.get("content_hash", ""),
        "status": metadata.get("status", "unprocessed"),
        "ingested_at": metadata.get("ingested_at", ""),
    }

    if existing is not None:
        docs[existing] = entry
    else:
        docs.append(entry)

    meta["documents"] = docs
    meta["document_count"] = len(docs)
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Rebuild body from documents list
    lines = ["# Raw Documents Index\n"]
    unprocessed = [d for d in docs if d.get("status") == "unprocessed"]
    compiled = [d for d in docs if d.get("status") == "compiled"]

    if unprocessed:
        lines.append(f"## Unprocessed ({len(unprocessed)})\n")
        for doc in unprocessed:
            lines.append(f"- [[{doc['path']}|{doc['title']}]] ({doc['source_type']})")
        lines.append("")

    if compiled:
        lines.append(f"## Compiled ({len(compiled)})\n")
        for doc in compiled:
            lines.append(f"- [[{doc['path']}|{doc['title']}]] ({doc['source_type']})")
        lines.append("")

    body = "\n".join(lines)
    write_frontmatter(index_path, meta, body)


def get_unprocessed_docs(vault_root: Path) -> list[dict[str, Any]]:
    """Get list of unprocessed raw documents from the index."""
    index_path = vault_root / RAW_INDEX
    if not index_path.exists():
        return []

    meta, _ = read_frontmatter(index_path)
    docs = meta.get("documents", [])
    return [d for d in docs if d.get("status") == "unprocessed"]


def mark_doc_compiled(
    vault_root: Path, doc_path: str, compiled_to: list[str] | None = None
) -> None:
    """Mark a raw document as compiled in the index."""
    index_path = vault_root / RAW_INDEX
    if not index_path.exists():
        return

    meta, body = read_frontmatter(index_path)
    docs = meta.get("documents", [])

    for doc in docs:
        if doc.get("path") == doc_path:
            doc["status"] = "compiled"
            if compiled_to:
                doc["compiled_to"] = compiled_to
            break

    meta["documents"] = docs
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Rebuild body
    update_raw_index(vault_root, doc_path, {
        "title": next((d["title"] for d in docs if d["path"] == doc_path), ""),
        "source_type": next((d["source_type"] for d in docs if d["path"] == doc_path), ""),
        "content_hash": next((d["content_hash"] for d in docs if d["path"] == doc_path), ""),
        "status": "compiled",
        "ingested_at": next((d["ingested_at"] for d in docs if d["path"] == doc_path), ""),
    })
