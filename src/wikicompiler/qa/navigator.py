"""Index-guided article retrieval for Q&A."""

from __future__ import annotations

from pathlib import Path

from ..vault.frontmatter import read_frontmatter
from ..vault.paths import WIKI_SUMMARIES, WIKI_DIR


def load_summaries(vault_root: Path) -> str:
    """Load the wiki summaries file content."""
    summaries_path = vault_root / WIKI_SUMMARIES
    if not summaries_path.exists():
        return "No summaries file found. The wiki may be empty."

    _, body = read_frontmatter(summaries_path)
    return body


def load_article(vault_root: Path, article_path: str) -> str:
    """Load a wiki article's full content."""
    full_path = vault_root / article_path
    if not full_path.exists():
        # Try adding .md extension
        full_path = vault_root / f"{article_path}.md"
    if not full_path.exists():
        return f"Article not found: {article_path}"

    try:
        meta, body = read_frontmatter(full_path)
        header = f"# {meta.get('title', full_path.stem)}\n"
        header += f"Category: {meta.get('category', 'unknown')}\n"
        header += f"Tags: {', '.join(meta.get('tags', []))}\n\n"
        return header + body
    except Exception:
        return full_path.read_text(encoding="utf-8")


def list_articles(vault_root: Path) -> list[dict]:
    """List all wiki articles with basic metadata."""
    wiki_dir = vault_root / WIKI_DIR
    articles = []

    if not wiki_dir.exists():
        return articles

    for md_file in wiki_dir.rglob("*.md"):
        if md_file.name.startswith("_"):
            continue
        rel_path = str(md_file.relative_to(vault_root))
        try:
            meta, _ = read_frontmatter(md_file)
            articles.append({
                "path": rel_path,
                "title": meta.get("title", md_file.stem),
                "category": meta.get("category", ""),
                "summary": meta.get("summary", ""),
            })
        except Exception:
            articles.append({
                "path": rel_path,
                "title": md_file.stem,
                "category": "",
                "summary": "",
            })

    return articles
