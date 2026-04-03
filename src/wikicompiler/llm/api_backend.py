"""Anthropic API backend with tool-use support."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import anthropic

from .base import BaseLLMBackend, LLMResponse
from .tools import ToolHandler


class APIBackend(BaseLLMBackend):
    """Direct Anthropic SDK backend with agentic tool-use loops."""

    def __init__(self, vault_root: Path, model: str = "claude-sonnet-4-20250514"):
        super().__init__(vault_root, model)
        self.client = anthropic.Anthropic()
        self.tool_handler = ToolHandler(vault_root)

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if tools:
            kwargs["tools"] = tools

        response = self._call_with_retry(kwargs)
        return self._parse_response(response)

    def agentic_loop(
        self,
        system_prompt: str,
        initial_message: str,
        tools: list[dict[str, Any]] | None = None,
        tool_handler: Any | None = None,
        max_turns: int = 20,
        max_tokens: int = 8192,
    ) -> list[LLMResponse]:
        handler = tool_handler or self.tool_handler
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": initial_message}
        ]
        responses: list[LLMResponse] = []

        for _ in range(max_turns):
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools

            response = self._call_with_retry(kwargs)
            parsed = self._parse_response(response)
            responses.append(parsed)

            # Add assistant message to conversation
            messages.append({"role": "assistant", "content": response.content})

            # Check if there are tool calls to process
            tool_use_blocks = [
                block for block in response.content
                if getattr(block, "type", None) == "tool_use"
            ]

            if not tool_use_blocks:
                break  # LLM is done

            # Execute tools and add results
            tool_results = []
            for block in tool_use_blocks:
                result = handler.handle(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            messages.append({"role": "user", "content": tool_results})

        return responses

    def _call_with_retry(
        self, kwargs: dict[str, Any], max_retries: int = 3
    ) -> Any:
        """Call the API with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                return self.client.messages.create(**kwargs)
            except anthropic.RateLimitError:
                if attempt < max_retries - 1:
                    time.sleep(2 ** (attempt + 1))
                else:
                    raise
            except anthropic.APIConnectionError:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse an Anthropic API response into LLMResponse."""
        text_parts = []
        tool_calls = []

        for block in response.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
            elif getattr(block, "type", None) == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        return LLMResponse(
            content="\n".join(text_parts),
            tool_calls=tool_calls if tool_calls else None,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            model=response.model,
        )
