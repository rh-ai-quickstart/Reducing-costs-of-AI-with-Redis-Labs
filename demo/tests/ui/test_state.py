"""Tests for Streamlit session-state helpers."""

from __future__ import annotations

import pytest

from services.agent_runner import AgentRunResult
from services.cost_metrics import RequestCostSnapshot, SessionCostTotals, empty_totals
from services.queue_client import QueueTask
from ui.state.agent_state import AgentTabState
from ui.state.queue_state import QueueTabState
from ui.state.router_state import RouterCacheState


def test_agent_tab_state_tracks_run_lifecycle(session_state):
    result = AgentRunResult(
        answer="Coverage applies.",
        model="test-complex",
        usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        cost_usd=0.01,
        latency_ms=250.0,
    )

    assert not AgentTabState.is_running()
    assert AgentTabState.pending_question() is None
    assert AgentTabState.last_result() is None

    AgentTabState.start_run("Will rental be covered?")
    assert AgentTabState.is_running()
    assert AgentTabState.pending_question() == "Will rental be covered?"

    AgentTabState.finish_run(result)
    assert not AgentTabState.is_running()
    assert AgentTabState.pending_question() is None
    assert AgentTabState.last_result() == result


def test_router_cache_state_pop_pending(session_state):
    RouterCacheState.queue_question("Hello?", force_miss=True)
    question, force_miss = RouterCacheState.pop_pending()

    assert question == "Hello?"
    assert force_miss is True
    assert RouterCacheState.PENDING_QUESTION not in session_state


def test_router_cache_state_record_turn(session_state):
    RouterCacheState.ensure_defaults()
    snap = RequestCostSnapshot(
        question="Q",
        route="simple",
        cached=False,
        path_label="Router → Simple model",
        model="test-simple",
        actual_cost=0.001,
        baseline_cost=0.01,
        saved=0.009,
        input_tokens=50,
        output_tokens=30,
        total_tokens=80,
    )
    totals = empty_totals()

    RouterCacheState.record_turn(
        question="Q",
        answer="A",
        outcome={"route": "simple"},
        cost_snap=snap,
        totals=totals,
    )

    assert RouterCacheState.last_outcome() == {"route": "simple"}
    assert RouterCacheState.last_cost() == snap
    assert RouterCacheState.messages() == [
        {"role": "user", "content": "Q"},
        {"role": "assistant", "content": "A"},
    ]
    assert RouterCacheState.pending_feedback() == {"question": "Q", "answer": "A"}
    assert session_state[RouterCacheState.COST_SAVED] == totals.total_saved


@pytest.mark.parametrize(
    ("outcome", "expected_stage"),
    [
        (None, None),
        ({"route": "simple"}, "route"),
        ({"route": "blocked"}, "route"),
        ({"route": "complex", "cached": True}, "cache"),
        ({"route": "complex", "cached": False}, "agent"),
    ],
)
def test_router_cache_active_pipeline_stage(session_state, outcome, expected_stage):
    if outcome is not None:
        session_state[RouterCacheState.LAST_OUTCOME] = outcome

    assert RouterCacheState.active_pipeline_stage() == expected_stage


def test_router_cache_reset_counters(session_state):
    RouterCacheState.ensure_defaults()
    session_state[RouterCacheState.MESSAGES] = [{"role": "user", "content": "hi"}]
    session_state[RouterCacheState.LAST_OUTCOME] = {"route": "simple"}

    RouterCacheState.reset_counters()

    assert RouterCacheState.messages() == []
    assert RouterCacheState.last_outcome() is None
    assert RouterCacheState.last_cost() is None
    assert RouterCacheState.get_totals().request_count == 0


def test_queue_tab_state_tracks_tasks_and_polling(session_state):
    QueueTabState.ensure_defaults()
    tasks = [
        QueueTask(task_id="task-1", question="First"),
        QueueTask(task_id="task-2", question="Second"),
    ]

    QueueTabState.set_tasks(tasks)
    QueueTabState.reset_logs("Worker connected")
    QueueTabState.start_polling()

    assert QueueTabState.tasks() == tasks
    assert QueueTabState.logs() == ["Worker connected"]
    assert QueueTabState.is_polling()

    QueueTabState.stop_polling()
    assert not QueueTabState.is_polling()
