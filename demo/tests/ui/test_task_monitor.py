"""Tests for production queue UI helpers."""

from __future__ import annotations

import pytest

from services.queue_client import QueueTask
from ui.components.task_monitor import (
    append_worker_logs,
    latest_event,
    render_event_timeline,
    task_status_emoji,
)


@pytest.mark.parametrize(
    ("status", "emoji"),
    [
        ("PENDING", "🟡"),
        ("PROCESSING", "🔵"),
        ("COMPLETED", "🟢"),
        ("FAILED", "🔴"),
        ("TIMEOUT", "🟠"),
        ("CANCELLED", "⚫"),
        ("UNKNOWN", "⚪"),
    ],
)
def test_task_status_emoji(status, emoji):
    assert task_status_emoji(status) == emoji


def test_append_worker_logs_deduplicates(session_state):
    tasks = [
        QueueTask(
            task_id="abcd1234-5678",
            question="Test question",
            updates=["Worker started", "Worker finished"],
        ),
        QueueTask(
            task_id="efgh9876-5432",
            question="Another question",
            updates=["Worker started"],
        ),
    ]

    append_worker_logs(tasks, log_key="queue_logs")
    append_worker_logs(tasks, log_key="queue_logs")

    logs = session_state["queue_logs"]
    assert len(logs) == 3
    assert logs[0] == "[abcd1234] Worker started"
    assert logs[1] == "[abcd1234] Worker finished"
    assert logs[2] == "[efgh9876] Worker started"


def test_latest_event_returns_most_recent_or_placeholder():
    with_events = QueueTask(
        task_id="abcd1234", question="q", updates=["Classifying...", "route=simple"]
    )
    no_events = QueueTask(task_id="efgh5678", question="q")
    assert latest_event(with_events) == "route=simple"
    assert latest_event(no_events) == "—"


def test_render_event_timeline_no_crash_when_events_absent():
    # No tasks carry updates → renders nothing, must not raise.
    render_event_timeline([QueueTask(task_id="abcd1234", question="q")])
