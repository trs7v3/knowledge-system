"""Wikilink parsing and generation for Obsidian-compatible markdown."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Matches [[target]] or [[target|display text]]
WIKILINK_PATTERN = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]")


@dataclass
class WikiLink:
    target: str  # The link target (page name or path)
    display: str | None = None  # Optional display text

    def __str__(self) -> str:
        if self.display:
            return f"[[{self.target}|{self.display}]]"
        return f"[[{self.target}]]"


def extract_wikilinks(text: str) -> list[WikiLink]:
    """Extract all wikilinks from markdown text."""
    return [
        WikiLink(target=m.group(1).strip(), display=m.group(2))
        for m in WIKILINK_PATTERN.finditer(text)
    ]


def make_wikilink(target: str, display: str | None = None) -> str:
    """Create a wikilink string."""
    return str(WikiLink(target=target, display=display))


def replace_wikilinks(
    text: str, replacements: dict[str, str]
) -> str:
    """Replace wikilink targets according to a mapping.

    replacements maps old_target -> new_target.
    """

    def _replace(m: re.Match) -> str:
        target = m.group(1).strip()
        display = m.group(2)
        new_target = replacements.get(target, target)
        if display:
            return f"[[{new_target}|{display}]]"
        return f"[[{new_target}]]"

    return WIKILINK_PATTERN.sub(_replace, text)


def find_backlinks(
    target_name: str, files: dict[str, str]
) -> list[str]:
    """Find all files that link to the given target.

    Args:
        target_name: The article name to search for.
        files: Mapping of file_path -> file_content.

    Returns:
        List of file paths that contain a wikilink to target_name.
    """
    results = []
    for path, content in files.items():
        links = extract_wikilinks(content)
        for link in links:
            if link.target == target_name or link.target.endswith(f"/{target_name}"):
                results.append(path)
                break
    return results
