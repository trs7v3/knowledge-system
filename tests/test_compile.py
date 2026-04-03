"""Tests for the compilation pipeline."""

from __future__ import annotations

from pathlib import Path


def test_indexer_rebuild(tmp_vault: Path):
    """Test that index rebuilding works with articles present."""
    from wikicompiler.vault.frontmatter import write_frontmatter, read_frontmatter
    from wikicompiler.compile.indexer import rebuild_indices

    # Create a sample wiki article
    write_frontmatter(
        tmp_vault / "wiki" / "concepts" / "gradient-descent.md",
        {
            "title": "Gradient Descent",
            "category": "concepts",
            "tags": ["optimization", "ml"],
            "summary": "Iterative optimization algorithm.",
        },
        "# Gradient Descent\n\nAn iterative optimization algorithm.\n",
    )

    write_frontmatter(
        tmp_vault / "wiki" / "entities" / "openai.md",
        {
            "title": "OpenAI",
            "category": "entities",
            "tags": ["company", "ai"],
            "summary": "AI research company.",
        },
        "# OpenAI\n\nAn AI research company.\n",
    )

    rebuild_indices(tmp_vault)

    # Check master index
    meta, body = read_frontmatter(tmp_vault / "wiki" / "_index.md")
    assert meta["article_count"] == 2
    assert "Gradient Descent" in body
    assert "OpenAI" in body

    # Check summaries
    _, summaries = read_frontmatter(tmp_vault / "wiki" / "_summaries.md")
    assert "Gradient Descent" in summaries
    assert "OpenAI" in summaries

    # Check category index
    meta, body = read_frontmatter(tmp_vault / "wiki" / "concepts" / "_index.md")
    assert meta["article_count"] == 1
    assert "Gradient Descent" in body


def test_linker_scan(tmp_vault: Path):
    """Test wikilink scanning."""
    from wikicompiler.vault.frontmatter import write_frontmatter
    from wikicompiler.compile.linker import scan_and_link

    write_frontmatter(
        tmp_vault / "wiki" / "concepts" / "a.md",
        {"title": "A"},
        "Article A links to [[b]] and [[c]].",
    )
    write_frontmatter(
        tmp_vault / "wiki" / "concepts" / "b.md",
        {"title": "B"},
        "Article B links to [[a]].",
    )

    graph = scan_and_link(tmp_vault)
    assert "wiki/concepts/a.md" in graph
    assert "b" in graph["wiki/concepts/a.md"]
    assert "c" in graph["wiki/concepts/a.md"]
    assert "a" in graph["wiki/concepts/b.md"]


def test_find_broken_links(tmp_vault: Path):
    """Test broken link detection."""
    from wikicompiler.vault.frontmatter import write_frontmatter
    from wikicompiler.compile.linker import find_broken_links

    write_frontmatter(
        tmp_vault / "wiki" / "concepts" / "exists.md",
        {"title": "Exists"},
        "Links to [[nonexistent-article]].",
    )

    broken = find_broken_links(tmp_vault)
    assert len(broken) >= 1
    targets = [t for _, t in broken]
    assert "nonexistent-article" in targets
