"""Visual pipeline diagram for the router → cache → agent journey."""

from __future__ import annotations

import streamlit as st

_STAGE_ORDER = ("route", "cache", "agent")
_STAGE_META = (
    ("route", "Semantic Router", "Classifies simple / complex / blocked", "⚡"),
    ("cache", "Semantic Cache", "Approved-answer lookup in Redis", "💾"),
    ("agent", "Complex Agent", "LangGraph + Vector Search tools", "🤖"),
)


def _stage_class(name: str, active_idx: int) -> str:
    """Return CSS class for a pipeline stage based on progress."""
    idx = _STAGE_ORDER.index(name)
    if active_idx < 0:
        return "journey-step pending"
    if idx < active_idx:
        return "journey-step complete"
    if idx == active_idx:
        return "journey-step active"
    return "journey-step pending"


def pipeline_diagram(active: str | None) -> None:
    """Render Route → Cache → Agent with the active stage highlighted."""
    active_idx = _STAGE_ORDER.index(active) if active in _STAGE_ORDER else -1
    rows: list[str] = []

    for key, title, subtitle, icon in _STAGE_META:
        rows.append(
            f'<div class="{_stage_class(key, active_idx)}">'
            f'<div class="step-header"><span class="step-icon">{icon}</span>{title}</div>'
            f'<div class="step-explanation">{subtitle}</div></div>'
        )
        if key != "agent":
            rows.append('<div class="journey-arrow">↓</div>')

    st.markdown(
        f'<div class="journey-pipeline">{"".join(rows)}</div>',
        unsafe_allow_html=True,
    )
