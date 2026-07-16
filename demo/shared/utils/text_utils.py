"""Small text-formatting helpers shared by UI and services."""

from __future__ import annotations


def truncate_text(text: str, max_len: int, *, ellipsis: str = "…") -> str:
    """Return *text* trimmed to *max_len* characters with an ellipsis when truncated."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + ellipsis
