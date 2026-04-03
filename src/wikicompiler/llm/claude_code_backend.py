"""Claude Code CLI backend — delegates LLM work to the `claude` CLI tool."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .base import BaseLLMBackend, LLMResponse
from ..util.logging import info, error


class ClaudeCodeBackend(BaseLLMBackend):
    """Backend that shells out to the `claude` CLI for LLM operations.

    This is useful when you want to use Claude Code's built-in capabilities
    (file editing, search, etc.) instead of managing tool-use loops directly.
    """

    def __init__(self, vault_root: Path, model: str = "claude-sonnet-4-20250514"):
        super().__init__(vault_root, model)

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """Run a single completion via claude CLI."""
        prompt = f"{system_prompt}\n\n{user_prompt}"
        result = self._run_claude(prompt)
        return LLMResponse(content=result, model="claude-code")

    def agentic_loop(
        self,
        system_prompt: str,
        initial_message: str,
        tools: list[dict[str, Any]] | None = None,
        tool_handler: Any | None = None,
        max_turns: int = 20,
        max_tokens: int = 8192,
    ) -> list[LLMResponse]:
        """Run an agentic session via claude CLI.

        Claude Code handles its own tool-use loop internally,
        so we just pass the full prompt and let it work.
        """
        prompt = f"{system_prompt}\n\n{initial_message}"
        result = self._run_claude(prompt)
        return [LLMResponse(content=result, model="claude-code")]

    def _run_claude(self, prompt: str) -> str:
        """Execute the claude CLI with the given prompt."""
        try:
            result = subprocess.run(
                [
                    "claude",
                    "--print",
                    "--dangerously-skip-permissions",
                    "--model", self.model,
                    prompt,
                ],
                capture_output=True,
                text=True,
                cwd=str(self.vault_root),
                timeout=300,
            )
            if result.returncode != 0:
                error(f"Claude CLI error: {result.stderr}")
                return f"Error running claude CLI: {result.stderr}"
            return result.stdout
        except FileNotFoundError:
            return (
                "Error: 'claude' CLI not found. Install Claude Code or "
                "switch to the 'api' backend in .wiki.toml."
            )
        except subprocess.TimeoutExpired:
            return "Error: Claude CLI timed out after 300 seconds."


def generate_claude_code_prompt(
    system_prompt: str, user_prompt: str, vault_root: Path
) -> str:
    """Generate a prompt suitable for manual Claude Code usage.

    Returns a formatted prompt the user can copy-paste into Claude Code,
    or that can be saved as instructions in CLAUDE.md.
    """
    return f"""\
# Wiki Compiler Task

Working directory: {vault_root}

## System Context
{system_prompt}

## Task
{user_prompt}

## Important
- All file operations should be within the vault directory
- Always include YAML frontmatter in .md files
- Use [[wikilinks]] for cross-references
- Update index files after making changes
"""
