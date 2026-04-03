"""LLM-powered Q&A against the wiki."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..llm import create_backend
from ..llm.prompts import QA_SYSTEM, QA_USER, QA_MARP_USER, QA_CHART_USER
from ..llm.tools import VAULT_TOOLS, ToolHandler
from ..util.config import Config
from ..util.logging import status


def ask_question(
    vault_root: Path,
    config: Config,
    question: str,
    output_format: str = "text",
) -> str:
    """Ask a question against the wiki and get an answer.

    Args:
        vault_root: Path to vault.
        config: Configuration.
        question: The question to ask.
        output_format: "text", "marp", or "chart".

    Returns:
        The answer content (markdown, Marp slides, or chart JSON).
    """
    # Use Q&A model
    qa_config = Config(vault_path=config.vault_path, llm=config.llm)
    qa_config.llm.model = config.llm.qa_model
    backend = create_backend(qa_config)

    # Select prompt based on output format
    if output_format == "marp":
        user_prompt = QA_MARP_USER.format(question=question)
    elif output_format == "chart":
        user_prompt = QA_CHART_USER.format(question=question)
    else:
        user_prompt = QA_USER.format(question=question)

    tool_handler = ToolHandler(vault_root)

    with status("Researching..."):
        responses = backend.agentic_loop(
            system_prompt=QA_SYSTEM,
            initial_message=user_prompt,
            tools=VAULT_TOOLS,
            tool_handler=tool_handler,
            max_turns=15,
        )

    # Collect the final text response
    answer_parts = []
    for resp in responses:
        if resp.content:
            answer_parts.append(resp.content)

    return answer_parts[-1] if answer_parts else "No answer could be generated."
