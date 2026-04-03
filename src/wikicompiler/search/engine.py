"""Search query execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from whoosh.qparser import MultifieldParser

from .indexer import open_index


@dataclass
class SearchResult:
    path: str
    title: str
    category: str
    summary: str
    snippet: str
    score: float


def search(vault_root: Path, query: str, limit: int = 20) -> list[SearchResult]:
    """Execute a search query against the wiki index.

    Returns a list of SearchResult objects sorted by relevance.
    """
    ix = open_index(vault_root)

    parser = MultifieldParser(
        ["title", "body", "summary", "tags"],
        schema=ix.schema,
    )
    parsed_query = parser.parse(query)

    results = []
    with ix.searcher() as searcher:
        hits = searcher.search(parsed_query, limit=limit)
        for hit in hits:
            snippet = hit.highlights("body", top=3) if hit.get("body") else ""
            results.append(
                SearchResult(
                    path=hit["path"],
                    title=hit.get("title", ""),
                    category=hit.get("category", ""),
                    summary=hit.get("summary", ""),
                    snippet=snippet,
                    score=hit.score,
                )
            )

    return results
