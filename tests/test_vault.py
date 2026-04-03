"""Tests for vault utilities."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_slug():
    from wikicompiler.vault.paths import slug

    assert slug("Hello World") == "hello-world"
    assert slug("  spaces  and -- dashes  ") == "spaces-and-dashes"
    assert slug("Special!@#$Characters") == "specialcharacters"
    assert slug("Already-Kebab-Case") == "already-kebab-case"


def test_init_vault_dirs(tmp_path: Path):
    from wikicompiler.vault.paths import init_vault_dirs, WIKI_CATEGORIES

    vault = tmp_path / "vault"
    vault.mkdir()
    init_vault_dirs(vault)

    assert (vault / "raw" / "articles").is_dir()
    assert (vault / "raw" / "papers").is_dir()
    assert (vault / "wiki").is_dir()
    assert (vault / "output").is_dir()
    assert (vault / "assets").is_dir()
    for cat in WIKI_CATEGORIES:
        assert (vault / "wiki" / cat).is_dir()


def test_safe_write_and_read(tmp_vault: Path):
    from wikicompiler.vault.paths import safe_write, safe_read

    content = "Hello, wiki!"
    path = safe_write(tmp_vault, "test/file.md", content)
    assert path.exists()
    assert safe_read(tmp_vault, "test/file.md") == content


def test_safe_write_rejects_outside_vault(tmp_vault: Path):
    from wikicompiler.vault.paths import safe_write

    with pytest.raises(ValueError, match="outside vault"):
        safe_write(tmp_vault, "../escape.md", "malicious")


def test_path_traversal_prefix_bypass(tmp_path: Path):
    """Ensure /vault-evil is not treated as inside /vault."""
    from wikicompiler.vault.paths import ensure_within_vault

    vault = tmp_path / "vault"
    vault.mkdir()
    evil = tmp_path / "vault-evil"
    evil.mkdir()
    target = evil / "secret.txt"
    target.write_text("secret")

    with pytest.raises(ValueError, match="outside vault"):
        ensure_within_vault(vault, target)


def test_tool_handler_rejects_traversal(tmp_vault: Path):
    """Ensure LLM tools cannot escape the vault."""
    from wikicompiler.llm.tools import ToolHandler

    handler = ToolHandler(tmp_vault)

    result = handler.handle("read_file", {"path": "../../etc/passwd"})
    assert "Error" in result

    result = handler.handle("write_file", {"path": "../evil.md", "content": "bad"})
    assert "Error" in result

    result = handler.handle("read_file", {"path": "/etc/passwd"})
    assert "Error" in result

    result = handler.handle("write_file", {"path": "test.sh", "content": "#!/bin/bash"})
    assert "Error" in result  # .sh not in allowed extensions


def test_frontmatter_roundtrip(tmp_vault: Path):
    from wikicompiler.vault.frontmatter import write_frontmatter, read_frontmatter

    path = tmp_vault / "test.md"
    meta = {"title": "Test", "tags": ["a", "b"]}
    body = "# Test\n\nBody content."

    write_frontmatter(path, meta, body)
    read_meta, read_body = read_frontmatter(path)

    assert read_meta["title"] == "Test"
    assert read_meta["tags"] == ["a", "b"]
    assert "Body content." in read_body


def test_wikilink_extraction():
    from wikicompiler.vault.wikilinks import extract_wikilinks

    text = "See [[gradient-descent]] and [[self-attention|Self-Attention]] for details."
    links = extract_wikilinks(text)

    assert len(links) == 2
    assert links[0].target == "gradient-descent"
    assert links[0].display is None
    assert links[1].target == "self-attention"
    assert links[1].display == "Self-Attention"


def test_wikilink_replacement():
    from wikicompiler.vault.wikilinks import replace_wikilinks

    text = "See [[old-name]] and [[other]]."
    result = replace_wikilinks(text, {"old-name": "new-name"})
    assert "[[new-name]]" in result
    assert "[[other]]" in result


def test_hashing():
    from wikicompiler.util.hashing import hash_content

    h1 = hash_content("hello")
    h2 = hash_content("hello")
    h3 = hash_content("world")

    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64  # SHA-256 hex


def test_config_defaults(tmp_vault: Path):
    from wikicompiler.util.config import load_config

    config = load_config(tmp_vault)
    assert config.llm.model == "claude-sonnet-4-20250514"
    assert config.llm.backend == "api"
    assert config.compile.categories == ["concepts", "entities", "techniques", "references"]


def test_obsidian_config(tmp_vault: Path):
    import json

    app_json = tmp_vault / ".obsidian" / "app.json"
    assert app_json.exists()
    data = json.loads(app_json.read_text())
    assert data["useMarkdownLinks"] is False
