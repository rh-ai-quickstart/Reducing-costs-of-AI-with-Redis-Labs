"""ROI cost panels for the router & cache tab."""

from __future__ import annotations

import streamlit as st

from services.cost_metrics import RequestCostSnapshot, SessionCostTotals
from services.pricing import default_pricing, format_cost
from utils.text_utils import truncate_text


def render_session_metrics(totals: SessionCostTotals) -> None:
    """Show cumulative session savings and deflection breakdown."""
    st.markdown("##### Session cost summary")
    pricing = default_pricing()
    st.caption(
        f"**Baseline** = every question through complex model "
        f"({pricing['complex'].display_name}) with agent context (~2k chars + answer). "
        f"**Actual** = what ran. "
        f"Rates from ROI_* env: simple ${pricing['simple'].input_per_million:.2f}/"
        f"${pricing['simple'].output_per_million:.2f} · complex ${pricing['complex'].input_per_million:.2f}/"
        f"${pricing['complex'].output_per_million:.2f} per 1M in/out tokens."
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Total saved", format_cost(totals.total_saved))
    m2.metric("💸 Actual spend", format_cost(totals.actual_spend))
    m3.metric("📊 Always-complex est.", format_cost(totals.baseline_spend))
    deflected = totals.simple_count + totals.blocked_count + totals.cache_hit_count
    m4.metric("🛡️ Deflected", f"{deflected}/{totals.request_count or 0}")

    if totals.request_count:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Simple", totals.simple_count)
        c2.metric("Blocked", totals.blocked_count)
        c3.metric("Cache hits", totals.cache_hit_count)
        c4.metric("Complex", totals.complex_count)
    else:
        st.info("Send a test question below — cost metrics update after each pipeline run.")


def render_last_request_cost(snap: RequestCostSnapshot) -> None:
    """Show per-request cost delta versus the always-complex baseline."""
    st.markdown("##### Last request")
    cols = st.columns(5)
    cols[0].metric("Path", snap.path_label)
    cols[1].metric("This request", format_cost(snap.actual_cost))
    cols[2].metric("If always complex", format_cost(snap.baseline_cost))
    cols[3].metric("Saved", format_cost(snap.saved))
    cols[4].metric("Savings", f"{snap.savings_pct:.0f}%")

    detail = st.columns(2)
    actual_note = "estimated" if snap.tokens_estimated else "from API"
    detail[0].caption(
        f"**Actual tokens** ({actual_note}): {snap.total_tokens:,} "
        f"(in {snap.input_tokens:,} / out {snap.output_tokens:,}) · "
        f"model: {snap.model or 'none'}"
    )
    detail[1].caption(
        f"**Baseline tokens** (complex counterfactual): {snap.baseline_total_tokens:,} "
        f"(in {snap.baseline_input_tokens:,} / out {snap.baseline_output_tokens:,})"
    )

    meta = st.columns(2)
    if snap.latency_ms is not None:
        meta[0].caption(f"Latency: **{snap.latency_ms:.0f} ms**")
    meta[1].caption(f"Route: **{snap.route}** · cached={snap.cached}")


def render_history_table(totals: SessionCostTotals, *, max_rows: int = 12) -> None:
    """Render a compact table of recent request cost snapshots."""
    if not totals.history:
        return

    st.markdown("##### Request history")
    st.dataframe(
        [
            {
                "Path": h.path_label,
                "Actual": format_cost(h.actual_cost),
                "Baseline": format_cost(h.baseline_cost),
                "Saved": format_cost(h.saved),
                "Tokens": h.total_tokens,
                "Latency (ms)": h.latency_ms if h.latency_ms is not None else "—",
                "Question": truncate_text(h.question, 50),
            }
            for h in reversed(totals.history[-max_rows:])
        ],
        use_container_width=True,
        hide_index=True,
    )
