"""Session keys and accessors for Tab 2 (router & semantic cache)."""

from __future__ import annotations

import streamlit as st

from insurance_pipeline import InsurancePipeline
from services.cost_metrics import RequestCostSnapshot, SessionCostTotals, empty_totals


class RouterCacheState:
    """Manages Tab 2 session state: pipeline singleton, chat, and ROI counters."""

    PIPELINE = "pipeline"
    MESSAGES = "t2_messages"
    LAST_OUTCOME = "t2_last_outcome"
    LAST_COST = "t2_last_cost"
    COST_TOTALS = "t2_cost_totals"
    PENDING_QUESTION = "t2_pending_question"
    FORCE_MISS = "t2_force_miss"
    PENDING_FEEDBACK = "t2_pending_feedback"
    COST_SAVED = "cost_saved"

    @classmethod
    def ensure_defaults(cls) -> None:
        """Initialize empty collections on first visit."""
        if cls.MESSAGES not in st.session_state:
            st.session_state[cls.MESSAGES] = []
        if cls.LAST_OUTCOME not in st.session_state:
            st.session_state[cls.LAST_OUTCOME] = None
        if cls.LAST_COST not in st.session_state:
            st.session_state[cls.LAST_COST] = None

    @classmethod
    def get_pipeline(cls) -> InsurancePipeline:
        """Return a process-wide pipeline instance cached in session state."""
        if cls.PIPELINE not in st.session_state:
            st.session_state[cls.PIPELINE] = InsurancePipeline()
        return st.session_state[cls.PIPELINE]

    @classmethod
    def get_totals(cls) -> SessionCostTotals:
        if cls.COST_TOTALS not in st.session_state:
            st.session_state[cls.COST_TOTALS] = empty_totals()
        return st.session_state[cls.COST_TOTALS]

    @classmethod
    def set_totals(cls, totals: SessionCostTotals) -> None:
        st.session_state[cls.COST_TOTALS] = totals
        st.session_state[cls.COST_SAVED] = totals.total_saved

    @classmethod
    def reset_counters(cls) -> None:
        """Clear ROI metrics and chat history."""
        st.session_state[cls.COST_TOTALS] = empty_totals()
        st.session_state[cls.LAST_COST] = None
        st.session_state[cls.MESSAGES] = []
        st.session_state[cls.LAST_OUTCOME] = None

    @classmethod
    def queue_question(cls, question: str, *, force_miss: bool) -> None:
        st.session_state[cls.PENDING_QUESTION] = question
        st.session_state[cls.FORCE_MISS] = force_miss

    @classmethod
    def pop_pending(cls) -> tuple[str | None, bool]:
        """Return and clear any deferred question submitted via buttons."""
        question = st.session_state.pop(cls.PENDING_QUESTION, None)
        force_miss = st.session_state.pop(cls.FORCE_MISS, False)
        return question, force_miss

    @classmethod
    def record_turn(
        cls,
        *,
        question: str,
        answer: str,
        outcome: dict,
        cost_snap: RequestCostSnapshot,
        totals: SessionCostTotals,
    ) -> None:
        """Append chat messages and persist the latest outcome + cost snapshot."""
        st.session_state[cls.LAST_OUTCOME] = outcome
        st.session_state[cls.MESSAGES].append({"role": "user", "content": question})
        st.session_state[cls.MESSAGES].append({"role": "assistant", "content": answer})
        st.session_state[cls.PENDING_FEEDBACK] = {"question": question, "answer": answer}
        st.session_state[cls.LAST_COST] = cost_snap
        cls.set_totals(totals)

    @classmethod
    def messages(cls) -> list[dict]:
        return st.session_state.get(cls.MESSAGES, [])

    @classmethod
    def last_outcome(cls) -> dict | None:
        return st.session_state.get(cls.LAST_OUTCOME)

    @classmethod
    def last_cost(cls) -> RequestCostSnapshot | None:
        return st.session_state.get(cls.LAST_COST)

    @classmethod
    def pending_feedback(cls) -> dict | None:
        return st.session_state.get(cls.PENDING_FEEDBACK)

    @classmethod
    def clear_feedback(cls) -> None:
        st.session_state.pop(cls.PENDING_FEEDBACK, None)

    @classmethod
    def active_pipeline_stage(cls) -> str | None:
        """Map the last outcome to the highlighted diagram stage."""
        outcome = cls.last_outcome()
        if not outcome:
            return None

        route = outcome.get("route")
        if route in {"simple", "blocked"}:
            return "route"
        if outcome.get("cached"):
            return "cache"
        if route == "complex":
            return "agent"
        return None
