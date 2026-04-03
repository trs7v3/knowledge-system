"""Tool definitions for LLM agentic calls.

These tools allow the LLM to read/write/search the vault during
compilation, Q&A, and linting operations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..vault.paths import ensure_within_vault, safe_write

# Tool definitions in Anthropic API format
VAULT_TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file in the vault. Returns the full text content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path from vault root, e.g. 'wiki/concepts/gradient-descent.md'",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write or overwrite a file in the vault. Use for creating or updating wiki articles. Content must include YAML frontmatter for .md files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path from vault root.",
                },
                "content": {
                    "type": "string",
                    "description": "Full file content to write (including frontmatter for .md files).",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_dir",
        "description": "List files and subdirectories in a vault directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative directory path from vault root, e.g. 'wiki/concepts'.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "search_files",
        "description": "Search for files containing a text query. Returns matching file paths and snippets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Text to search for across all vault files.",
                },
                "directory": {
                    "type": "string",
                    "description": "Optional: limit search to this directory (relative to vault root).",
                },
            },
            "required": ["query"],
        },
    },
]


class ToolHandler:
    """Executes tool calls from the LLM against the vault filesystem."""

    def __init__(self, vault_root: Path):
        self.vault_root = vault_root

    def handle(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Execute a tool call and return the result as a string."""
        try:
            if tool_name == "read_file":
                return self._read_file(tool_input["path"])
            elif tool_name == "write_file":
                return self._write_file(tool_input["path"], tool_input["content"])
            elif tool_name == "list_dir":
                return self._list_dir(tool_input["path"])
            elif tool_name == "search_files":
                return self._search_files(
                    tool_input["query"], tool_input.get("directory")
                )
            else:
                return f"Error: Unknown tool '{tool_name}'"
        except Exception as e:
            return f"Error: {e}"

    def _read_file(self, rel_path: str) -> str:
        target = self.vault_root / rel_path
        ensure_within_vault(self.vault_root, target)
        if not target.exists():
            return f"Error: File not found: {rel_path}"
        return target.read_text(encoding="utf-8")

    def _write_file(self, rel_path: str, content: str) -> str:
        safe_write(self.vault_root, rel_path, content)
        return f"Successfully wrote {rel_path}"

    def _list_dir(self, rel_path: str) -> str:
        target = self.vault_root / rel_path
        ensure_within_vault(self.vault_root, target)
        if not target.is_dir():
            return f"Error: Not a directory: {rel_path}"
        entries = sorted(target.iterdir())
        lines = []
        for e in entries:
            prefix = "d " if e.is_dir() else "f "
            lines.append(f"{prefix}{e.name}")
        return "\n".join(lines) if lines else "(empty directory)"

    def _search_files(self, query: str, directory: str | None = None) -> str:
        search_root = self.vault_root
        if directory:
            search_root = self.vault_root / directory
            ensure_within_vault(self.vault_root, search_root)

        query_lower = query.lower()
        results = []
        for md_file in search_root.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                if query_lower in content.lower():
                    rel = md_file.relative_to(self.vault_root)
                    # Find first matching line for context
                    for line in content.splitlines():
                        if query_lower in line.lower():
                            snippet = line.strip()[:120]
                            results.append(f"{rel}: {snippet}")
                            break
                    if len(results) >= 20:
                        break
            except (UnicodeDecodeError, PermissionError):
                continue

        if not results:
            return f"No results found for '{query}'"
        return "\n".join(results)
