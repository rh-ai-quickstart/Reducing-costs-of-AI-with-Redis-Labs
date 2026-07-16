"""Outcome banners for pipeline routing decisions."""

from __future__ import annotations

import streamlit as st

from config import model_names


def outcome_banner(outcome: dict) -> None:
    """Show a colored banner summarizing the last router/cache/agent outcome."""
    models = model_names()
    route = outcome.get("route")
    cached = outcome.get("cached")

    if route == "blocked":
        st.error("🛑 Intercepted by Semantic Router — blocked prompt, no LLM invoked.")
        return

    if route == "simple":
        st.success(
            f"⚡ Intercepted by Semantic Router — {models['simple']} only (no agent)."
        )
        return

    if cached:
        dist = outcome.get("similarity_distance")
        extra = f" (distance={dist:.3f})" if dist is not None else ""
        st.success(f"💾 Semantic Cache Hit!{extra} Near-zero agent cost.")
        return

    if route == "complex":
        st.info(
            f"🤖 Cache miss — full complex agent path "
            f"({models['complex']} + Redis tools)."
        )
