"""Tests for the search system."""

from __future__ import annotations

from pathlib import Path


def test_search_index_build(tmp_vault: Path):
    """Test building and querying the search index."""
    from wikicompiler.vault.frontmatter import write_frontmatter
    from wikicompiler.search.indexer import build_index
    from wikicompiler.search.engine import search

    # Create sample articles
    write_frontmatter(
        tmp_vault / "wiki" / "concepts" / "neural-networks.md",
        {
            "title": "Neural Networks",
            "category": "concepts",
            "tags": ["ml", "deep-learning"],
            "summary": "Computing systems inspired by biological neural networks.",
        },
        "# Neural Networks\n\nNeural networks are computing systems inspired by biological neural networks.\n",
    )

    write_frontmatter(
        tmp_vault / "wiki" / "concepts" / "gradient-descent.md",
        {
            "title": "Gradient Descent",
            "category": "concepts",
            "tags": ["optimization"],
            "summary": "Optimization algorithm for training models.",
        },
        "# Gradient Descent\n\nGradient descent is an optimization algorithm.\n",
    )

    # Build index
    count = build_index(tmp_vault)
    assert count == 2

    # Search
    results = search(tmp_vault, "neural")
    assert len(results) >= 1
    assert results[0].title == "Neural Networks"

    results = search(tmp_vault, "optimization")
    assert len(results) >= 1
