"""Session keys and accessors for Tab 1 (baseline complex agent)."""

from __future__ import annotations

import streamlit as st

from services.agent_runner import AgentRunResult


class AgentTabState:
    """Centralizes Tab 1 `st.session_state` keys to avoid string drift."""

    RUNNING = "t1_running"
    QUESTION = "t1_question"
    LAST_RESULT = "t1_last_result"

    @classmethod
    def start_run(cls, question: str) -> None:
        """Mark a new agent run as in-flight."""
        st.session_state[cls.RUNNING] = True
        st.session_state[cls.QUESTION] = question

    @classmethod
    def finish_run(cls, result: AgentRunResult) -> None:
        """Persist the completed run and clear the in-flight flag."""
        st.session_state[cls.LAST_RESULT] = result
        st.session_state[cls.RUNNING] = False

    @classmethod
    def is_running(cls) -> bool:
        return bool(st.session_state.get(cls.RUNNING))

    @classmethod
    def pending_question(cls) -> str | None:
        if cls.is_running():
            return st.session_state.get(cls.QUESTION)
        return None

    @classmethod
    def last_result(cls) -> AgentRunResult | None:
        return st.session_state.get(cls.LAST_RESULT)
