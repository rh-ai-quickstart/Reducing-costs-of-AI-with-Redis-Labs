"""Tab 4 — Production queue monitor (Redis Agent Kit)."""

from __future__ import annotations

import streamlit as st

from services.constants import TERMINAL_TASK_STATUSES
from services.queue_client import (
    PRODUCTION_QUESTIONS,
    QUEUE_NAME,
    WORKER_TASK_NAME,
    enqueue_batch,
    redis_stream_metrics,
    refresh_tasks,
)
from ui.components import (
    append_worker_logs,
    render_queue_metrics,
    render_task_table,
)
from ui.state import QueueTabState

_POLL_INTERVAL_S = 0.6


def _batch_is_complete(tasks: list) -> bool:
    return bool(tasks) and all(t.status in TERMINAL_TASK_STATUSES for t in tasks)


def _render_enqueue_controls() -> bool:
    """Return True when a new batch was enqueued (caller should rerun)."""
    count = st.slider(
        "Questions to fire",
        min_value=5,
        max_value=10,
        value=8,
        key="t4_count",
        help="How many preset production questions to enqueue in one batch to Redis Streams.",
    )

    if not st.button(
        "Simulate Production Traffic",
        type="primary",
        key="t4_simulate",
        help="Enqueue tasks to the insurance queue — RAK workers process them asynchronously.",
    ):
        return False

    questions = PRODUCTION_QUESTIONS[:count]
    try:
        with st.spinner(f"Enqueuing {len(questions)} tasks to Redis Streams…"):
            QueueTabState.set_tasks(enqueue_batch(questions))
    except Exception as exc:
        st.error(
            f"Failed to enqueue tasks: {exc}. "
            "On OpenShift, redeploy with `roiDashboard.gitSync.forceRefresh=true` "
            "so the dashboard PVC picks up the latest demo code."
        )
        return False

    QueueTabState.reset_logs(
        f"Enqueued {len(questions)} tasks to Redis Streams "
        f"(Docket handler: {WORKER_TASK_NAME}, queue: {QUEUE_NAME})…"
    )
    QueueTabState.start_polling()
    return True


def _render_task_panel(*, live: bool) -> bool:
    """Render metrics, task table, and logs. Returns True when the batch is finished."""
    render_queue_metrics(redis_stream_metrics())

    tasks = QueueTabState.tasks()
    if live and tasks:
        tasks = refresh_tasks(tasks)
        QueueTabState.set_tasks(tasks)
        append_worker_logs(tasks, log_key=QueueTabState.LOGS)

    if tasks:
        st.subheader("Task queue")
        render_task_table(tasks)

    logs = QueueTabState.logs()
    if logs:
        st.subheader("Worker log")
        st.code("\n".join(logs[-40:]), language=None)

    batch_done = _batch_is_complete(tasks)
    if batch_done:
        done = sum(1 for t in tasks if t.status == "COMPLETED")
        st.success(f"Batch complete — {done}/{len(tasks)} tasks succeeded.")
    elif live and tasks and QueueTabState.is_polling():
        in_flight = sum(1 for t in tasks if t.status not in TERMINAL_TASK_STATUSES)
        st.caption(
            f"Live refresh every ~{_POLL_INTERVAL_S:.1f}s — "
            f"{in_flight}/{len(tasks)} task(s) still in flight."
        )

    return batch_done


def _render_live_monitor() -> None:
    """Fragment with periodic refresh while tasks are in flight."""
    poll_interval = _POLL_INTERVAL_S if QueueTabState.is_polling() else None

    @st.fragment(run_every=poll_interval)
    def _task_monitor() -> None:
        live = QueueTabState.is_polling()
        batch_done = _render_task_panel(live=live)
        if batch_done and QueueTabState.is_polling():
            QueueTabState.stop_polling()
            st.rerun()

    _task_monitor()


def render() -> None:
    st.header("Production Topology: Redis Agent Kit Workers")
    st.caption(
        "Same pipeline as Tab 3 — decoupled via Redis Streams so the UI never blocks on inference."
    )

    QueueTabState.ensure_defaults()

    if _render_enqueue_controls():
        st.rerun()

    _render_live_monitor()

    st.info(
        "Requires a running RAK worker: "
        "`rak worker --name insurance --tasks insurance_worker:tasks --concurrency 4`"
    )
