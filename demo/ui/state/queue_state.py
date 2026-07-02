"""Session keys and accessors for Tab 3 (production queue monitor)."""

from __future__ import annotations

import streamlit as st

from services.queue_client import QueueTask


class QueueTabState:
    """Tracks enqueued tasks, worker logs, and live-polling flag for Tab 3."""

    TASKS = "queue_tasks"
    LOGS = "queue_logs"
    POLLING = "queue_polling"

    @classmethod
    def ensure_defaults(cls) -> None:
        if cls.TASKS not in st.session_state:
            st.session_state[cls.TASKS] = []
        if cls.LOGS not in st.session_state:
            st.session_state[cls.LOGS] = []
        if cls.POLLING not in st.session_state:
            st.session_state[cls.POLLING] = False

    @classmethod
    def tasks(cls) -> list[QueueTask]:
        return list(st.session_state.get(cls.TASKS, []))

    @classmethod
    def set_tasks(cls, tasks: list[QueueTask]) -> None:
        st.session_state[cls.TASKS] = tasks

    @classmethod
    def logs(cls) -> list[str]:
        return st.session_state.get(cls.LOGS, [])

    @classmethod
    def reset_logs(cls, first_line: str) -> None:
        st.session_state[cls.LOGS] = [first_line]

    @classmethod
    def is_polling(cls) -> bool:
        return bool(st.session_state.get(cls.POLLING))

    @classmethod
    def start_polling(cls) -> None:
        st.session_state[cls.POLLING] = True

    @classmethod
    def stop_polling(cls) -> None:
        st.session_state[cls.POLLING] = False
