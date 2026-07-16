"""Router + cache + agent pipeline facade (notebook 02).

Implementation lives in :mod:`insurance_bot`; this module is the stable import
path for the Streamlit demo and notebooks.
"""

from __future__ import annotations

from typing import Any

from insurance_bot import InsurancePipeline, build_pipeline

__all__ = ["InsurancePipeline", "build_pipeline", "submit_feedback"]


def submit_feedback(
    pipeline: InsurancePipeline,
    question: str,
    answer: str,
    *,
    thumbs_up: bool,
    metadata: dict | None = None,
) -> dict[str, Any]:
    """Explicitly store (or skip) an answer in the semantic cache."""
    if not thumbs_up:
        return {"stored": False, "reason": "negative feedback ignored"}
    pipeline.store_response(
        question,
        answer,
        metadata=metadata or {"source": "ui", "approved": True},
    )
    return {"stored": True}
