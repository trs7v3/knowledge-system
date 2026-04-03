"""LLM backend factory."""

from __future__ import annotations

from pathlib import Path

from .base import BaseLLMBackend, LLMResponse
from ..util.config import Config


def create_backend(config: Config) -> BaseLLMBackend:
    """Create an LLM backend based on configuration."""
    vault_root = config.vault_path

    if config.llm.backend == "claude-code":
        from .claude_code_backend import ClaudeCodeBackend
        return ClaudeCodeBackend(vault_root, model=config.llm.model)
    else:
        from .api_backend import APIBackend
        return APIBackend(vault_root, model=config.llm.model)


__all__ = ["BaseLLMBackend", "LLMResponse", "create_backend"]
