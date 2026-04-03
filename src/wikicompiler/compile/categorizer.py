"""Auto-categorization of content into wiki categories."""

from __future__ import annotations

import json
from typing import Any

from ..llm.base import BaseLLMBackend
from ..llm.prompts import CATEGORIZE_USER


def categorize_content(
    backend: BaseLLMBackend, content: str
) -> list[dict[str, str]]:
    """Use the LLM to categorize content into wiki article proposals.

    Returns:
        List of dicts with keys: title, category, summary
    """
    response = backend.complete(
        system_prompt="You are a document categorizer. Respond only with valid JSON.",
        user_prompt=CATEGORIZE_USER.format(content=content[:10000]),
    )

    try:
        proposals = json.loads(response.content)
        if isinstance(proposals, list):
            return [
                {
                    "title": p.get("title", "Untitled"),
                    "category": p.get("category", "concepts"),
                    "summary": p.get("summary", ""),
                }
                for p in proposals
            ]
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: single article in concepts
    return [{"title": "Untitled", "category": "concepts", "summary": ""}]
