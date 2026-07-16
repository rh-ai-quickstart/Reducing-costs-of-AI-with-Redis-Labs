"""Queue task table and worker log helpers for Tab 4 (production queue)."""

from __future__ import annotations

import streamlit as st

from services.constants import TERMINAL_TASK_STATUSES
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


def latest_event(task: QueueTask) -> str:
    """Most recent stream event the worker emitted for this task."""
    return task.updates[-1] if task.updates else "—"


def render_task_table(tasks: list[QueueTask], *, question_max_len: int = 60) -> None:
    """Render the live task queue as a Streamlit dataframe."""
    st.dataframe(
        [
            {
                "Status": f"{task_status_emoji(t.status)} {t.status}",
                "Task ID": t.task_id[:12],
                "Route": t.route or "—",
                "Cached": t.cached if t.cached is not None else "—",
                "Latest event": latest_event(t),
                "Question": truncate_text(t.question, question_max_len),
            }
            for t in tasks
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_event_timeline(tasks: list[QueueTask], *, question_max_len: int = 50) -> None:
    """Per-task timeline of the stream events each RAK worker emitted.

    Reads the events RAK publishes to each task's Redis stream (classify →
    route → decision) so you can see what the worker is doing, live.
    """
    with_events = [t for t in tasks if t.updates]
    if not with_events:
        return

    st.markdown("##### Stream events")
    st.caption(
        "Each task publishes progress events to its Redis stream as the worker "
        "handles it. In-flight tasks stay open so you can watch them advance."
    )
    for t in with_events:
        header = (
            f"{task_status_emoji(t.status)} {t.task_id[:8]} · "
            f"{truncate_text(t.question, question_max_len)}"
        )
        with st.expander(header, expanded=t.status not in TERMINAL_TASK_STATUSES):
            for step, event in enumerate(t.updates, start=1):
                st.markdown(f"`{step}` {event}")


def render_queue_metrics(metrics: dict) -> None:
    """Show Redis stream depth and active worker count."""
    st.markdown("##### Queue health")
    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Stream key",
        metrics.get("stream_key", "—"),
        help="Redis Streams key where Tab 4 tasks are published (Docket queue).",
    )
    m2.metric(
        "Queue depth",
        metrics.get("queue_length", 0),
        help="Messages waiting in the stream — should drain as workers consume tasks.",
    )
    m3.metric(
        "Active workers",
        metrics.get("active_workers", 0),
        help="RAK consumer processes in the worker group. Zero means Tab 4 tasks will not run.",
    )


def append_worker_logs(tasks: list[QueueTask], *, log_key: str = "queue_logs") -> None:
    """Append unseen worker update lines into session state."""
    logs: list[str] = st.session_state.setdefault(log_key, [])
    for row in tasks:
        for update in row.updates:
            line = f"[{row.task_id[:8]}] {update}"
            if line not in logs:
                logs.append(line)
