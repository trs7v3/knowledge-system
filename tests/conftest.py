"""Shared test fixtures."""

from __future__ import annotations

import pytest
from pathlib import Path


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Create a temporary vault directory with basic structure."""
    from wikicompiler.vault.paths import init_vault_dirs
    from wikicompiler.vault.obsidian import init_obsidian_config
    from wikicompiler.util.config import write_default_config

    vault = tmp_path / "vault"
    vault.mkdir()
    init_vault_dirs(vault)
    init_obsidian_config(vault)
    write_default_config(vault)

    return vault
