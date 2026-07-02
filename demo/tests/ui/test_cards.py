"""Tests for preflight status cards."""

from __future__ import annotations

from services.preflight import CheckResult
from ui.components.cards import status_card


def test_status_card_renders_check_details(monkeypatch):
    captured: list[str] = []

    monkeypatch.setattr(
        "ui.components.cards.st.markdown",
        lambda html, *, unsafe_allow_html: captured.append(html),
    )

    status_card(
        CheckResult(
            name="Redis",
            status="connected",
            detail="PONG",
            latency_ms=12.5,
        )
    )

    assert len(captured) == 1
    html = captured[0]
    assert "Redis" in html
    assert "Connected" in html
    assert "12 ms" in html
    assert "PONG" in html


def test_status_card_shows_dash_when_latency_missing(monkeypatch):
    captured: list[str] = []

    monkeypatch.setattr(
        "ui.components.cards.st.markdown",
        lambda html, *, unsafe_allow_html: captured.append(html),
    )

    status_card(
        CheckResult(
            name="Worker",
            status="idle",
            detail="No active workers",
            latency_ms=None,
        )
    )

    assert "—" in captured[0]
    assert "Not running" in captured[0]
