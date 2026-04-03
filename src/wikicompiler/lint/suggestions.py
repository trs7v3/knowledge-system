"""New article candidate suggestions based on wiki analysis."""

from __future__ import annotations

from pathlib import Path

from ..llm import create_backend
from ..llm.prompts import LINT_SUGGESTIONS_SYSTEM
from ..llm.tools import VAULT_TOOLS, ToolHandler
from ..util.config import Config
from ..util.logging import status


def suggest_articles(vault_root: Path, config: Config) -> str:
    """Use LLM to suggest new articles that would enhance the wiki.

    Returns a structured report string.
    """
    backend = create_backend(config)
    tool_handler = ToolHandler(vault_root)

    with status("Analyzing wiki for article suggestions..."):
        responses = backend.agentic_loop(
            system_prompt=LINT_SUGGESTIONS_SYSTEM,
            initial_message="Analyze the wiki and suggest new articles. Read wiki/_summaries.md first to understand what exists.",
            tools=VAULT_TOOLS,
            tool_handler=tool_handler,
            max_turns=15,
        )

    if responses:
        return responses[-1].content
    return "No suggestions at this time."
