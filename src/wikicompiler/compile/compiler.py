"""Main wiki compilation orchestrator.

Reads raw documents, determines what needs compilation,
and drives the LLM agentic loop to produce wiki articles.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ..llm import create_backend
from ..llm.prompts import COMPILE_SYSTEM, COMPILE_USER
from ..llm.tools import VAULT_TOOLS, ToolHandler
from ..ingest.metadata import get_unprocessed_docs, mark_doc_compiled
from ..util.config import Config
from ..util.hashing import hash_file
from ..util.logging import info, success, warn, error, status
from ..vault.frontmatter import read_frontmatter
from ..vault.paths import WIKI_DIR, COMPILATION_STATE


def compile_wiki(
    vault_root: Path,
    config: Config,
    full: bool = False,
    dry_run: bool = False,
    specific_doc: str | None = None,
) -> list[str]:
    """Compile raw documents into wiki articles.

    Args:
        vault_root: Path to the vault root.
        config: Configuration.
        full: If True, recompile all documents.
        dry_run: If True, just show what would be compiled.
        specific_doc: If set, only compile this specific document.

    Returns:
        List of produced wiki article paths.
    """
    # Determine what needs compilation
    work_list = _get_work_list(vault_root, full, specific_doc)

    if not work_list:
        info("Nothing to compile. All documents are up to date.")
        return []

    if dry_run:
        info(f"Would compile {len(work_list)} document(s):")
        for doc in work_list:
            info(f"  - {doc['path']} ({doc.get('title', 'untitled')})")
        return []

    info(f"Compiling {len(work_list)} document(s)...")

    # Create LLM backend
    compile_config = Config(
        vault_path=config.vault_path,
        llm=config.llm,
    )
    compile_config.llm.model = config.llm.compilation_model
    backend = create_backend(compile_config)

    all_produced: list[str] = []

    for doc in work_list:
        produced = _compile_document(vault_root, backend, doc)
        all_produced.extend(produced)
        mark_doc_compiled(vault_root, doc["path"], compiled_to=produced)
        success(f"Compiled {doc['path']} -> {len(produced)} article(s)")

    # Update indices after compilation
    from .indexer import rebuild_indices
    rebuild_indices(vault_root)

    # Update compilation state
    _update_compilation_state(vault_root, work_list, all_produced)

    success(f"Compilation complete. Produced {len(all_produced)} article(s).")
    return all_produced


def _get_work_list(
    vault_root: Path, full: bool, specific_doc: str | None
) -> list[dict[str, Any]]:
    """Determine which documents need compilation."""
    if specific_doc:
        # Compile just this one document
        doc_path = vault_root / specific_doc
        if not doc_path.exists():
            error(f"Document not found: {specific_doc}")
            return []
        meta, _ = read_frontmatter(doc_path)
        return [{"path": specific_doc, **meta}]

    if full:
        # Recompile everything
        from ..vault.paths import RAW_DIR
        raw_dir = vault_root / RAW_DIR
        docs = []
        for md_file in raw_dir.rglob("*.md"):
            if md_file.name.startswith("_"):
                continue
            try:
                meta, _ = read_frontmatter(md_file)
                rel_path = str(md_file.relative_to(vault_root))
                docs.append({"path": rel_path, **meta})
            except Exception:
                continue
        return docs

    # Incremental: unprocessed documents from index + untracked files on disk
    unprocessed = get_unprocessed_docs(vault_root)

    # Also discover raw .md files not tracked in the index at all
    # (e.g. dropped in by Obsidian Web Clipper or manual copy)
    from ..vault.paths import RAW_DIR
    from ..ingest.metadata import update_raw_index, create_raw_metadata

    raw_dir = vault_root / RAW_DIR
    if raw_dir.exists():
        indexed_paths = {d["path"] for d in unprocessed}
        # Also get compiled paths so we don't re-add them
        index_path = vault_root / "raw/_index.md"
        all_indexed_paths = set()
        if index_path.exists():
            idx_meta, _ = read_frontmatter(index_path)
            all_indexed_paths = {d["path"] for d in idx_meta.get("documents", [])}

        for md_file in raw_dir.rglob("*.md"):
            if md_file.name.startswith("_"):
                continue
            rel_path = str(md_file.relative_to(vault_root))
            if rel_path not in all_indexed_paths:
                # Auto-register this untracked file
                try:
                    meta, content = read_frontmatter(md_file)
                except Exception:
                    content = md_file.read_text(encoding="utf-8")
                    meta = {}

                if meta.get("status") != "compiled":
                    title = meta.get("title", md_file.stem.replace("-", " ").title())
                    reg_meta = create_raw_metadata(
                        source_type=meta.get("source_type", "markdown"),
                        title=title,
                        content=content,
                    )
                    update_raw_index(vault_root, rel_path, reg_meta)
                    unprocessed.append({"path": rel_path, **reg_meta})
                    info(f"Auto-registered untracked file: {rel_path}")

    return unprocessed


def _compile_document(
    vault_root: Path,
    backend: Any,
    doc: dict[str, Any],
) -> list[str]:
    """Compile a single raw document using the LLM.

    Returns list of produced wiki article relative paths.
    """
    doc_path = vault_root / doc["path"]
    if not doc_path.exists():
        error(f"Document not found: {doc['path']}")
        return []

    # Read document content
    try:
        _, content = read_frontmatter(doc_path)
    except Exception:
        content = doc_path.read_text(encoding="utf-8")

    # Build the user prompt
    user_prompt = COMPILE_USER.format(
        source_path=doc["path"],
        content=content[:50000],  # Truncate very long docs
    )

    tool_handler = ToolHandler(vault_root)

    with status(f"Compiling {doc.get('title', doc['path'])}..."):
        responses = backend.agentic_loop(
            system_prompt=COMPILE_SYSTEM,
            initial_message=user_prompt,
            tools=VAULT_TOOLS,
            tool_handler=tool_handler,
            max_turns=15,
        )

    # Find which wiki files were written by checking tool calls
    produced = []
    for resp in responses:
        if resp.tool_calls:
            for call in resp.tool_calls:
                if call["name"] == "write_file":
                    path = call["input"].get("path", "")
                    if path.startswith(WIKI_DIR) and path not in produced:
                        produced.append(path)

    return produced


def _update_compilation_state(
    vault_root: Path,
    compiled_docs: list[dict[str, Any]],
    produced_articles: list[str],
) -> None:
    """Update the compilation state tracking file."""
    state_path = vault_root / COMPILATION_STATE
    now = datetime.now(timezone.utc).isoformat()

    if state_path.exists():
        existing = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
    else:
        existing = {}

    existing["last_compile"] = now
    docs_state = existing.get("docs", {})

    for doc in compiled_docs:
        docs_state[doc["path"]] = {
            "content_hash": doc.get("content_hash", ""),
            "last_compiled": now,
            "status": "compiled",
        }

    existing["docs"] = docs_state
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(yaml.dump(existing, default_flow_style=False), encoding="utf-8")
