"""Index and summaries file generation for the wiki."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..vault.frontmatter import read_frontmatter, write_frontmatter
from ..vault.paths import WIKI_DIR, WIKI_INDEX, WIKI_SUMMARIES, WIKI_CATEGORIES
from ..util.logging import info, success


def rebuild_indices(vault_root: Path) -> None:
    """Rebuild all index files and the summaries file."""
    articles = _collect_articles(vault_root)

    _rebuild_master_index(vault_root, articles)
    _rebuild_summaries(vault_root, articles)
    _rebuild_category_indices(vault_root, articles)

    success(f"Rebuilt indices for {len(articles)} article(s)")


def _collect_articles(vault_root: Path) -> list[dict]:
    """Collect metadata from all wiki articles."""
    wiki_dir = vault_root / WIKI_DIR
    articles = []

    for md_file in wiki_dir.rglob("*.md"):
        if md_file.name.startswith("_"):
            continue

        rel_path = str(md_file.relative_to(vault_root))
        try:
            meta, body = read_frontmatter(md_file)
        except Exception:
            meta = {}
            body = md_file.read_text(encoding="utf-8")

        # Determine category from path
        parts = rel_path.split("/")
        category = parts[1] if len(parts) > 2 else "uncategorized"

        articles.append({
            "path": rel_path,
            "path_no_ext": rel_path.replace(".md", ""),
            "name": md_file.stem,
            "title": meta.get("title", md_file.stem.replace("-", " ").title()),
            "category": meta.get("category", category),
            "summary": meta.get("summary", ""),
            "tags": meta.get("tags", []),
        })

    return sorted(articles, key=lambda a: (a["category"], a["title"]))


def _rebuild_master_index(vault_root: Path, articles: list[dict]) -> None:
    """Rebuild wiki/_index.md."""
    now = datetime.now(timezone.utc).isoformat()

    meta = {
        "type": "index",
        "updated_at": now,
        "article_count": len(articles),
    }

    lines = ["# Wiki Index\n"]

    # Group by category
    by_category: dict[str, list[dict]] = {}
    for article in articles:
        cat = article["category"]
        by_category.setdefault(cat, []).append(article)

    for cat in sorted(by_category.keys()):
        lines.append(f"## {cat.title()} ({len(by_category[cat])})\n")
        for article in by_category[cat]:
            summary = f" — {article['summary']}" if article["summary"] else ""
            lines.append(
                f"- [[{article['path_no_ext']}|{article['title']}]]{summary}"
            )
        lines.append("")

    write_frontmatter(vault_root / WIKI_INDEX, meta, "\n".join(lines))


def _rebuild_summaries(vault_root: Path, articles: list[dict]) -> None:
    """Rebuild wiki/_summaries.md."""
    now = datetime.now(timezone.utc).isoformat()

    meta = {
        "type": "summaries",
        "updated_at": now,
    }

    lines = [
        "# Article Summaries\n",
        "| Article | Category | Summary |",
        "|---------|----------|---------|",
    ]

    for article in articles:
        link = f"[[{article['path_no_ext']}|{article['title']}]]"
        lines.append(f"| {link} | {article['category']} | {article['summary']} |")

    write_frontmatter(vault_root / WIKI_SUMMARIES, meta, "\n".join(lines))


def _rebuild_category_indices(vault_root: Path, articles: list[dict]) -> None:
    """Rebuild per-category _index.md files."""
    now = datetime.now(timezone.utc).isoformat()

    # Group by category
    by_category: dict[str, list[dict]] = {}
    for article in articles:
        cat = article["category"]
        by_category.setdefault(cat, []).append(article)

    for cat in WIKI_CATEGORIES:
        cat_articles = by_category.get(cat, [])

        meta = {
            "type": "index",
            "category": cat,
            "updated_at": now,
            "article_count": len(cat_articles),
        }

        lines = [f"# {cat.title()} Index\n"]
        if cat_articles:
            for article in cat_articles:
                summary = f" — {article['summary']}" if article["summary"] else ""
                lines.append(
                    f"- [[{article['path_no_ext']}|{article['title']}]]{summary}"
                )
        else:
            lines.append("No articles yet.")
        lines.append("")

        index_path = vault_root / WIKI_DIR / cat / "_index.md"
        write_frontmatter(index_path, meta, "\n".join(lines))
