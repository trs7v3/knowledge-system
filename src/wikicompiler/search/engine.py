"""Search query execution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from markupsafe import Markup, escape
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
            raw_snippet = hit.highlights("body", top=3) if hit.get("body") else ""
            snippet = _sanitize_snippet(raw_snippet)
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


def _sanitize_snippet(html: str) -> str:
    """Sanitize Whoosh highlight HTML: escape everything except <b> tags.

    Whoosh wraps matched terms in <b class="match term0">...</b>.
    We preserve those but escape all other HTML to prevent XSS.
    """
    if not html:
        return ""
    # Extract Whoosh <b> highlight tags, escape everything else
    _HIGHLIGHT_RE = re.compile(r'<b class="match \w+">(.*?)</b>')
    parts = _HIGHLIGHT_RE.split(html)
    safe_parts = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Non-highlighted text: escape HTML
            safe_parts.append(str(escape(part)))
        else:
            # Highlighted match: wrap in <b> with escaped content
            safe_parts.append(f'<b class="match">{escape(part)}</b>')
    return Markup("".join(safe_parts))
