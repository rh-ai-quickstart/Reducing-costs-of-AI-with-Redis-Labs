"""Tests for router/cache outcome banners."""

from __future__ import annotations

import pytest

from ui.components.banners import outcome_banner


@pytest.fixture
def mock_model_names(monkeypatch):
    monkeypatch.setattr(
        "ui.components.banners.model_names",
        lambda: {"simple": "test-simple", "complex": "test-complex"},
    )


def test_outcome_banner_blocked(mock_model_names, monkeypatch):
    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "ui.components.banners.st.error",
        lambda msg: calls.append(("error", msg)),
    )
    monkeypatch.setattr(
        "ui.components.banners.st.success",
        lambda msg: calls.append(("success", msg)),
    )

    outcome_banner({"route": "blocked"})

    assert len(calls) == 1
    assert calls[0][0] == "error"
    assert "Semantic Router" in calls[0][1]


def test_outcome_banner_simple_route(mock_model_names, monkeypatch):
    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "ui.components.banners.st.success",
        lambda msg: calls.append(("success", msg)),
    )

    outcome_banner({"route": "simple"})

    assert len(calls) == 1
    assert "test-simple" in calls[0][1]


def test_outcome_banner_cache_hit(mock_model_names, monkeypatch):
    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "ui.components.banners.st.success",
        lambda msg: calls.append(("success", msg)),
    )

    outcome_banner({"route": "complex", "cached": True, "similarity_distance": 0.042})

    assert len(calls) == 1
    assert "Semantic Cache Hit" in calls[0][1]
    assert "distance=0.042" in calls[0][1]


def test_outcome_banner_complex_miss(mock_model_names, monkeypatch):
    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "ui.components.banners.st.info",
        lambda msg: calls.append(("info", msg)),
    )

    outcome_banner({"route": "complex", "cached": False})

    assert len(calls) == 1
    assert "test-complex" in calls[0][1]
    assert "Cache miss" in calls[0][1]
