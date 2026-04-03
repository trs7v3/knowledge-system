"""Obsidian vault configuration scaffolding."""

from __future__ import annotations

import json
from pathlib import Path

from .paths import OBSIDIAN_DIR


def init_obsidian_config(vault_root: Path) -> None:
    """Create minimal .obsidian/ configuration for the vault."""
    obsidian_dir = vault_root / OBSIDIAN_DIR
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    # app.json — core settings
    app_config = {
        "useMarkdownLinks": False,  # Use [[wikilinks]] not [](markdown links)
        "newLinkFormat": "shortest",
        "showFrontmatter": True,
        "readableLineLength": True,
        "strictLineBreaks": False,
    }
    _write_json(obsidian_dir / "app.json", app_config)

    # appearance.json
    appearance = {
        "baseFontSize": 16,
        "theme": "obsidian",
    }
    _write_json(obsidian_dir / "appearance.json", appearance)

    # community-plugins.json — empty list, user can add their own
    _write_json(obsidian_dir / "community-plugins.json", [])


def _write_json(path: Path, data: dict | list) -> None:
    """Write JSON config file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
