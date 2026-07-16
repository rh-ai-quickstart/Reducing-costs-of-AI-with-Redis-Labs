"""Session keys and accessors for Tab 2 (complex baseline agent)."""

from __future__ import annotations

import streamlit as st

from services.agent_runner import AgentRunResult


class AgentTabState:
    """Centralizes Tab 2 `st.session_state` keys to avoid string drift."""

    RUNNING = "t2_running"
    QUESTION = "t2_question"
    LAST_RESULT = "t2_last_result"

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
