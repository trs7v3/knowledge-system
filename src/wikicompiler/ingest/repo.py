"""Git repository summarization for ingestion."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def summarize_repo(repo_url: str) -> tuple[str, str]:
    """Clone a git repo and generate a markdown summary.

    Returns:
        (title, markdown_content)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        clone_dir = Path(tmpdir) / "repo"

        # Shallow clone
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(clone_dir)],
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )

        # Extract repo name
        title = clone_dir.name
        if title == "repo":
            title = repo_url.rstrip("/").split("/")[-1].replace(".git", "")

        parts = [f"# {title}\n", f"**Repository:** {repo_url}\n"]

        # Read README
        readme_content = _find_readme(clone_dir)
        if readme_content:
            parts.append("## README\n")
            parts.append(readme_content)
            parts.append("")

        # Directory structure (top 2 levels)
        tree = _dir_tree(clone_dir, max_depth=2)
        parts.append("## Directory Structure\n")
        parts.append(f"```\n{tree}\n```\n")

        # Key files summary
        key_files = _find_key_files(clone_dir)
        if key_files:
            parts.append("## Key Files\n")
            for name, content in key_files:
                parts.append(f"### {name}\n")
                parts.append(f"```\n{content[:2000]}\n```\n")

        return title, "\n".join(parts)


def _find_readme(repo_dir: Path) -> str | None:
    """Find and read the README file."""
    for name in ["README.md", "README.rst", "README.txt", "README"]:
        readme = repo_dir / name
        if readme.exists():
            return readme.read_text(encoding="utf-8", errors="replace")
    return None


def _dir_tree(root: Path, max_depth: int = 2, prefix: str = "") -> str:
    """Generate a simple directory tree string."""
    lines = []
    entries = sorted(
        [e for e in root.iterdir() if not e.name.startswith(".")],
        key=lambda e: (not e.is_dir(), e.name),
    )
    for i, entry in enumerate(entries[:30]):  # Limit entries
        connector = "|-- " if i < len(entries) - 1 else "`-- "
        lines.append(f"{prefix}{connector}{entry.name}")
        if entry.is_dir() and max_depth > 1:
            extension = "|   " if i < len(entries) - 1 else "    "
            subtree = _dir_tree(entry, max_depth - 1, prefix + extension)
            if subtree:
                lines.append(subtree)
    return "\n".join(lines)


def _find_key_files(repo_dir: Path) -> list[tuple[str, str]]:
    """Find and read key configuration/metadata files."""
    key_names = [
        "pyproject.toml", "package.json", "Cargo.toml",
        "go.mod", "Makefile", "Dockerfile",
    ]
    results = []
    for name in key_names:
        path = repo_dir / name
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="replace")
            results.append((name, content))
    return results
