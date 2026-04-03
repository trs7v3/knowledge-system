"""Missing data detection and completeness checking."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..llm import create_backend
from ..llm.prompts import LINT_COMPLETENESS_SYSTEM
from ..llm.tools import VAULT_TOOLS, ToolHandler
from ..util.config import Config
from ..util.logging import status


def check_completeness(vault_root: Path, config: Config) -> str:
    """Use LLM to find gaps and missing data in the wiki.

    Returns a structured report string.
    """
    backend = create_backend(config)
    tool_handler = ToolHandler(vault_root)

    with status("Checking wiki completeness..."):
        responses = backend.agentic_loop(
            system_prompt=LINT_COMPLETENESS_SYSTEM,
            initial_message="Analyze the wiki for completeness. Read wiki/_summaries.md first, then check articles for missing data and gaps.",
            tools=VAULT_TOOLS,
            tool_handler=tool_handler,
            max_turns=15,
        )

    if responses:
        return responses[-1].content
    return "No completeness issues found."
