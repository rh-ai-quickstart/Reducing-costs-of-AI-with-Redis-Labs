"""Tests for ROI cost panel rendering."""

from __future__ import annotations

from services.cost_metrics import RequestCostSnapshot, SessionCostTotals
from ui.components.cost_panels import render_history_table


def test_render_history_table_skips_when_empty(monkeypatch):
    dataframe_calls: list[list] = []

    monkeypatch.setattr(
        "ui.components.cost_panels.st.dataframe",
        lambda rows, **kwargs: dataframe_calls.append(rows),
    )
    monkeypatch.setattr(
        "ui.components.cost_panels.st.markdown",
        lambda *args, **kwargs: None,
    )

    render_history_table(SessionCostTotals())

    assert dataframe_calls == []


def test_render_history_table_shows_recent_rows(monkeypatch):
    rows_captured: list[list] = []

    monkeypatch.setattr(
        "ui.components.cost_panels.st.dataframe",
        lambda rows, **kwargs: rows_captured.append(rows),
    )
    monkeypatch.setattr(
        "ui.components.cost_panels.st.markdown",
        lambda *args, **kwargs: None,
    )

    history = [
        RequestCostSnapshot(
            question=f"Question {idx}",
            route="simple",
            cached=False,
            path_label="Router → Simple model",
            model="test-simple",
            actual_cost=0.001 * idx,
            baseline_cost=0.01,
            saved=0.01 - 0.001 * idx,
            input_tokens=50,
            output_tokens=20,
            total_tokens=70,
            latency_ms=float(idx * 10),
        )
        for idx in range(1, 4)
    ]
    totals = SessionCostTotals(history=history)

    render_history_table(totals, max_rows=2)

    assert len(rows_captured) == 1
    rows = rows_captured[0]
    assert len(rows) == 2
    assert rows[0]["Question"].startswith("Question 3")
    assert rows[1]["Question"].startswith("Question 2")
