"""OpenAI-compatible endpoint helpers."""

from __future__ import annotations


def openai_base_url(endpoint: str) -> str:
    """Normalize a chat-completions endpoint to the `/v1` base URL ChatOpenAI expects."""
    trimmed = endpoint.rstrip("/")
    for suffix in ("/chat/completions", "/completions"):
        if trimmed.endswith(suffix):
            trimmed = trimmed[: -len(suffix)]
            break
    return trimmed
