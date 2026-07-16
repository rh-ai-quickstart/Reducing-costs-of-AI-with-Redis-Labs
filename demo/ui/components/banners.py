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


def routing_detail(question: str, outcome: dict) -> None:
    """Show exactly what the router decided and which path actually executed.

    Makes the silent no-match → complex fallback visible, and echoes the
    question that was sent (presets otherwise never show it).
    """
    models = model_names()
    route = outcome.get("route")
    router_name = outcome.get("router_name")
    dist = outcome.get("router_distance")
    cached = outcome.get("cached")

    lines = [f"**Question sent:** {question}"]

    if cached and not router_name:
        lines.append("**Router:** skipped — the semantic cache answered first.")
    elif router_name:
        d = f"{dist:.3f}" if dist is not None else "?"
        lines.append(f"**Router matched** `{router_name}` at distance {d} (≤ threshold).")
    else:
        lines.append(
            "**Router: no route matched** above its distance threshold, so the "
            "request **defaulted to the complex agent**. A Simple or Blocked "
            "question can land here when it sits just outside every route's threshold."
        )

    if route == "blocked":
        lines.append("**Executed:** blocked → refusal returned, no LLM call.")
    elif route == "simple":
        lines.append(f"**Executed:** {models['simple']} only (agent skipped).")
    elif cached:
        d = outcome.get("similarity_distance")
        extra = f" at distance {d:.3f}" if d is not None else ""
        lines.append(f"**Executed:** semantic cache hit{extra} — agent skipped.")
    elif route == "complex":
        tools = outcome.get("tools_used") or []
        tool_txt = ", ".join(f"`{t}`" for t in tools) if tools else "none"
        lines.append(
            f"**Executed:** {models['complex']} agent. Redis tools fired: {tool_txt}."
        )

    usage = outcome.get("usage") or {}
    meta = []
    if usage.get("total_tokens"):
        meta.append(f"{usage['total_tokens']} tokens")
    if outcome.get("latency_ms"):
        meta.append(f"{outcome['latency_ms']:.0f} ms")
    if meta:
        lines.append("· ".join(meta))

    with st.expander("🔎 What happened (routing decision & path)", expanded=True):
        st.markdown("  \n".join(lines))


def route_definitions() -> None:
    """List the reference phrases and threshold that define each router route."""
    from insurance_bot import (
        BLOCKED_ROUTE_REFS,
        COMPLEX_ROUTE_REFS,
        SIMPLE_ROUTE_REFS,
    )

    with st.expander("📚 What defines each route? (semantic router references)"):
        st.caption(
            "The router embeds your question and compares it to these example "
            "phrases. The closest route within its distance threshold wins; "
            "if none qualifies, the request falls through to the complex agent."
        )
        for name, refs in (
            ("⚡ simple", SIMPLE_ROUTE_REFS),
            ("🤖 complex", COMPLEX_ROUTE_REFS),
            ("🛑 blocked", BLOCKED_ROUTE_REFS),
        ):
            st.markdown(f"**{name}**")
            st.markdown("\n".join(f"- {ref}" for ref in refs))
