"""Wikilink and backlink maintenance for the wiki."""

from __future__ import annotations

from pathlib import Path

from ..vault.paths import WIKI_DIR
from ..vault.wikilinks import extract_wikilinks, make_wikilink
from ..vault.frontmatter import read_frontmatter, write_frontmatter
from ..util.logging import info, warn


def scan_and_link(vault_root: Path) -> dict[str, list[str]]:
    """Scan all wiki articles and build a link graph.

    Returns:
        Dict mapping article_path -> list of linked article names.
    """
    wiki_dir = vault_root / WIKI_DIR
    link_graph: dict[str, list[str]] = {}

    for md_file in wiki_dir.rglob("*.md"):
        if md_file.name.startswith("_"):
            continue
        rel_path = str(md_file.relative_to(vault_root))
        content = md_file.read_text(encoding="utf-8")
        links = extract_wikilinks(content)
        link_graph[rel_path] = [link.target for link in links]

    return link_graph


def find_broken_links(vault_root: Path) -> list[tuple[str, str]]:
    """Find wikilinks that point to non-existent articles.

    Returns:
        List of (source_file, broken_target) tuples.
    """
    wiki_dir = vault_root / WIKI_DIR
    link_graph = scan_and_link(vault_root)

    # Build set of existing article names
    existing = set()
    for md_file in wiki_dir.rglob("*.md"):
        if md_file.name.startswith("_"):
            continue
        # Add both the full relative path and just the name
        rel = str(md_file.relative_to(vault_root))
        existing.add(rel)
        existing.add(rel.replace(".md", ""))
        existing.add(md_file.stem)

    broken = []
    for source, targets in link_graph.items():
        for target in targets:
            # Check if target resolves to an existing file
            if (
                target not in existing
                and f"{WIKI_DIR}/{target}" not in existing
                and f"{WIKI_DIR}/{target}.md" not in existing
                and not target.startswith("raw/")  # Raw links are OK
            ):
                broken.append((source, target))

    return broken


def find_orphaned_articles(vault_root: Path) -> list[str]:
    """Find wiki articles that have no inbound links."""
    link_graph = scan_and_link(vault_root)

    # Collect all link targets
    all_targets = set()
    for targets in link_graph.values():
        all_targets.update(targets)

    # Find articles not targeted by any link
    orphans = []
    for article_path in link_graph:
        name = Path(article_path).stem
        rel_no_ext = article_path.replace(".md", "")
        if (
            name not in all_targets
            and rel_no_ext not in all_targets
            and article_path not in all_targets
        ):
            orphans.append(article_path)

    return orphans


def generate_backlinks_section(
    vault_root: Path, article_path: str
) -> str:
    """Generate a backlinks section for an article."""
    link_graph = scan_and_link(vault_root)
    article_name = Path(article_path).stem

    backlinks = []
    for source, targets in link_graph.items():
        if source == article_path:
            continue
        for target in targets:
            if target == article_name or target.endswith(f"/{article_name}"):
                backlinks.append(source)
                break

    if not backlinks:
        return ""

    lines = ["\n## Backlinks\n"]
    for bl in sorted(backlinks):
        name = Path(bl).stem.replace("-", " ").title()
        link_target = bl.replace(".md", "")
        lines.append(f"- [[{link_target}|{name}]]")

    return "\n".join(lines)
