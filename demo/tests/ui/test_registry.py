"""Tests for the dashboard tab registry."""

from __future__ import annotations

from ui.registry import DASHBOARD_TABS, DashboardTab


def test_dashboard_tabs_are_ordered_and_unique():
    labels = [tab.label for tab in DASHBOARD_TABS]
    notebook_indices = [tab.notebook_index for tab in DASHBOARD_TABS]

    assert len(labels) == len(set(labels))
    assert notebook_indices == ["", "00", "01", "02", "03"]
    assert len(DASHBOARD_TABS) == 5


def test_each_tab_has_render_callable():
    for tab in DASHBOARD_TABS:
        assert isinstance(tab, DashboardTab)
        assert tab.label
        assert callable(tab.render)
