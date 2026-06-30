"""Status cards for infrastructure preflight results."""

from __future__ import annotations

import streamlit as st

from services.preflight import CheckResult, status_label


def status_card(result: CheckResult) -> None:
    """Render a single preflight check as a styled dashboard card."""
    badge = status_label(result)
    latency = f"{result.latency_ms:.0f} ms" if result.latency_ms is not None else "—"
    st.markdown(
        f"""
<div class="component-card">
  <h4>{result.name}</h4>
  <div class="component-stat"><span>Status</span><span>{badge}</span></div>
  <div class="component-stat"><span>Latency</span><span>{latency}</span></div>
  <div class="component-stat"><span>Detail</span><span>{result.detail}</span></div>
</div>
""",
        unsafe_allow_html=True,
    )
