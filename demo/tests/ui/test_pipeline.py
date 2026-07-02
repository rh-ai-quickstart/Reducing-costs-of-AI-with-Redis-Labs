"""Tests for the router → cache → agent pipeline diagram."""

from __future__ import annotations

import pytest

from ui.components.pipeline import _stage_class


@pytest.mark.parametrize(
    ("stage", "active_idx", "expected_suffix"),
    [
        ("route", -1, "pending"),
        ("cache", -1, "pending"),
        ("agent", -1, "pending"),
        ("route", 0, "active"),
        ("cache", 0, "pending"),
        ("agent", 0, "pending"),
        ("route", 1, "complete"),
        ("cache", 1, "active"),
        ("agent", 1, "pending"),
        ("route", 2, "complete"),
        ("cache", 2, "complete"),
        ("agent", 2, "active"),
    ],
)
def test_stage_class_reflects_pipeline_progress(stage, active_idx, expected_suffix):
    css = _stage_class(stage, active_idx)
    assert css.endswith(expected_suffix)


def test_pipeline_diagram_renders_html(monkeypatch):
    from ui.components.pipeline import pipeline_diagram

    captured: list[str] = []

    def fake_markdown(html: str, *, unsafe_allow_html: bool) -> None:
        captured.append(html)

    monkeypatch.setattr("ui.components.pipeline.st.markdown", fake_markdown)

    pipeline_diagram("cache")

    assert len(captured) == 1
    html = captured[0]
    assert "journey-pipeline" in html
    assert "Semantic Router" in html
    assert "Semantic Cache" in html
    assert "Complex Agent" in html
    assert 'class="journey-step complete"' in html
    assert 'class="journey-step active"' in html
