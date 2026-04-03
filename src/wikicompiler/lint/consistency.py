"""Cross-article consistency checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..compile.linker import find_broken_links, find_orphaned_articles
from ..vault.frontmatter import read_frontmatter
from ..vault.paths import WIKI_DIR


@dataclass
class LintIssue:
    severity: str  # "error", "warning", "info"
    category: str  # "broken_link", "orphan", "missing_frontmatter", etc.
    file: str
    message: str


def check_broken_links(vault_root: Path) -> list[LintIssue]:
    """Find broken wikilinks."""
    broken = find_broken_links(vault_root)
    return [
        LintIssue(
            severity="error",
            category="broken_link",
            file=source,
            message=f"Broken link to [[{target}]]",
        )
        for source, target in broken
    ]


def check_orphaned_articles(vault_root: Path) -> list[LintIssue]:
    """Find articles with no inbound links."""
    orphans = find_orphaned_articles(vault_root)
    return [
        LintIssue(
            severity="warning",
            category="orphan",
            file=path,
            message="Article has no inbound links",
        )
        for path in orphans
    ]


def check_frontmatter(vault_root: Path) -> list[LintIssue]:
    """Check that all wiki articles have required frontmatter fields."""
    required_fields = ["title", "category", "tags", "summary"]
    issues = []

    wiki_dir = vault_root / WIKI_DIR
    if not wiki_dir.exists():
        return issues

    for md_file in wiki_dir.rglob("*.md"):
        if md_file.name.startswith("_"):
            continue

        rel_path = str(md_file.relative_to(vault_root))
        try:
            meta, _ = read_frontmatter(md_file)
            for field in required_fields:
                if field not in meta or not meta[field]:
                    issues.append(
                        LintIssue(
                            severity="warning",
                            category="missing_frontmatter",
                            file=rel_path,
                            message=f"Missing frontmatter field: {field}",
                        )
                    )
        except Exception as e:
            issues.append(
                LintIssue(
                    severity="error",
                    category="parse_error",
                    file=rel_path,
                    message=f"Failed to parse frontmatter: {e}",
                )
            )

    return issues


def run_all_checks(vault_root: Path) -> list[LintIssue]:
    """Run all consistency checks."""
    issues = []
    issues.extend(check_broken_links(vault_root))
    issues.extend(check_orphaned_articles(vault_root))
    issues.extend(check_frontmatter(vault_root))
    return issues
