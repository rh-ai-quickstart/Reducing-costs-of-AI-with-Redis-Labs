"""Tab 0 — System readiness preflight."""

from __future__ import annotations

import streamlit as st

from config import model_names
from services.preflight import run_preflight_checks
from ui.components import status_card


def _render_summary(results: list) -> None:
    """Show a top-level pass/warn banner before the per-service cards."""
    if all(r.ok for r in results):
        st.success("All systems ready — Redis, models, and RAK worker are connected.")
    elif any(r.status == "idle" for r in results):
        st.warning(
            "Core services are up, but the RAK worker is not connected "
            "(Tab 3 will not process tasks)."
        )


def _render_status_grid(results: list) -> None:
    """Lay out four preflight cards in a 2×2 grid."""
    row1 = st.columns(2)
    row2 = st.columns(2)
    for col, result in zip(row1 + row2, results):
        with col:
            status_card(result)


def render() -> None:
    st.header("Infrastructure Preflight Verification")
    st.caption(
        "Confirms Redis, MaaS model gateways, and the RAK worker are live before running the demo."
    )

    if st.button("Run Preflight Checks", type="primary", key="run_preflight"):
        with st.spinner("Checking Redis, MaaS endpoints, and worker queue..."):
            st.session_state["preflight_results"] = run_preflight_checks()

    results = st.session_state.get("preflight_results")
    if not results:
        models = model_names()
        st.info(
            f"Click **Run Preflight Checks** to probe Redis, {models['simple']}, "
            f"{models['complex']}, and the insurance RAK worker."
        )
        return

    _render_summary(results)
    _render_status_grid(results)
