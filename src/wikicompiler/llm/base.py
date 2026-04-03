"""Base LLM backend interface — ABC for pluggable LLM integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class LLMResponse:
    """Standard response from an LLM call."""

    content: str
    tool_calls: list[dict[str, Any]] | None = None
    usage: dict[str, int] | None = None
    model: str = ""


class BaseLLMBackend(ABC):
    """Abstract base for LLM backends (API, Claude Code, etc.)."""

    def __init__(self, vault_root: Path, model: str = "claude-sonnet-4-20250514"):
        self.vault_root = vault_root
        self.model = model

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """Single completion call."""
        ...

    @abstractmethod
    def agentic_loop(
        self,
        system_prompt: str,
        initial_message: str,
        tools: list[dict[str, Any]] | None = None,
        tool_handler: Any | None = None,
        max_turns: int = 20,
        max_tokens: int = 8192,
    ) -> list[LLMResponse]:
        """Run an agentic tool-use loop until the LLM stops calling tools.

        Args:
            system_prompt: System instructions.
            initial_message: The first user message.
            tools: Tool definitions for the LLM.
            tool_handler: Callable that executes tool calls and returns results.
            max_turns: Safety limit on number of turns.
            max_tokens: Max tokens per response.

        Returns:
            List of all LLM responses in the conversation.
        """
        ...
