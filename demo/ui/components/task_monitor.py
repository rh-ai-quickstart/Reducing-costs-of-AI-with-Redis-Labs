"""Queue task table and worker log helpers for the production tab."""

from __future__ import annotations

import streamlit as st

from services.queue_client import QueueTask
from utils.text_utils import truncate_text

_STATUS_EMOJI = {
    "PENDING": "🟡",
    "PROCESSING": "🔵",
    "COMPLETED": "🟢",
    "FAILED": "🔴",
    "TIMEOUT": "🟠",
    "CANCELLED": "⚫",
}


def task_status_emoji(status: str) -> str:
    """Map a RAK task status string to a colored emoji prefix."""
    return _STATUS_EMOJI.get(status, "⚪")


def render_task_table(tasks: list[QueueTask], *, question_max_len: int = 60) -> None:
    """Render the live task queue as a Streamlit dataframe."""
    st.dataframe(
        [
            {
                "Status": f"{task_status_emoji(t.status)} {t.status}",
                "Task ID": t.task_id[:12],
                "Route": t.route or "—",
                "Cached": t.cached if t.cached is not None else "—",
                "Question": truncate_text(t.question, question_max_len),
            }
            for t in tasks
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_queue_metrics(metrics: dict) -> None:
    """Show Redis stream depth and active worker count."""
    st.markdown("##### Queue health")
    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Stream key",
        metrics.get("stream_key", "—"),
        help="Redis Streams key where Tab 3 tasks are published (Docket queue).",
    )
    m2.metric(
        "Queue depth",
        metrics.get("queue_length", 0),
        help="Messages waiting in the stream — should drain as workers consume tasks.",
    )
    m3.metric(
        "Active workers",
        metrics.get("active_workers", 0),
        help="RAK consumer processes in the worker group. Zero means Tab 3 tasks will not run.",
    )


def append_worker_logs(tasks: list[QueueTask], *, log_key: str = "queue_logs") -> None:
    """Append unseen worker update lines into session state."""
    logs: list[str] = st.session_state.setdefault(log_key, [])
    for row in tasks:
        for update in row.updates:
            line = f"[{row.task_id[:8]}] {update}"
            if line not in logs:
                logs.append(line)
