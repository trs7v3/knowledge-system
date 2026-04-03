"""Tests for the ingest pipeline."""

from __future__ import annotations

from pathlib import Path


def test_metadata_creation():
    from wikicompiler.ingest.metadata import create_raw_metadata

    meta = create_raw_metadata(
        source_type="web_article",
        title="Test Article",
        content="Some content here",
        source_url="https://example.com",
    )

    assert meta["title"] == "Test Article"
    assert meta["source_type"] == "web_article"
    assert meta["source_url"] == "https://example.com"
    assert meta["status"] == "unprocessed"
    assert "content_hash" in meta
    assert len(meta["content_hash"]) == 64


def test_raw_index_update(tmp_vault: Path):
    from wikicompiler.ingest.metadata import (
        create_raw_metadata,
        update_raw_index,
        get_unprocessed_docs,
    )
    from wikicompiler.vault.frontmatter import write_frontmatter
    from wikicompiler.vault.paths import RAW_INDEX

    # Create raw index first
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    write_frontmatter(
        tmp_vault / RAW_INDEX,
        {"type": "raw_index", "documents": [], "document_count": 0, "updated_at": now},
        "# Raw Documents Index\n",
    )

    meta = create_raw_metadata(
        source_type="web_article",
        title="Test",
        content="test content",
    )
    update_raw_index(tmp_vault, "raw/articles/test.md", meta)

    docs = get_unprocessed_docs(tmp_vault)
    assert len(docs) == 1
    assert docs[0]["path"] == "raw/articles/test.md"
    assert docs[0]["status"] == "unprocessed"


def test_file_ingest_markdown(tmp_vault: Path, tmp_path: Path):
    from wikicompiler.ingest.metadata import create_raw_metadata
    from wikicompiler.vault.frontmatter import write_frontmatter

    # Create a sample markdown file
    source = tmp_path / "sample.md"
    source.write_text("# My Article\n\nSome content about AI.", encoding="utf-8")

    # Simulate ingest
    content = source.read_text(encoding="utf-8")
    title = "My Article"
    meta = create_raw_metadata(
        source_type="markdown", title=title, content=content
    )

    dest = tmp_vault / "raw" / "articles" / "my-article.md"
    write_frontmatter(dest, meta, content)

    assert dest.exists()
    from wikicompiler.vault.frontmatter import read_frontmatter
    read_meta, body = read_frontmatter(dest)
    assert read_meta["title"] == "My Article"
    assert "Some content about AI" in body
