"""Tab registry — single source of truth for dashboard tabs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ui.tabs import agent, guide, production, readiness, router_cache


@dataclass(frozen=True)
class DashboardTab:
    """One Streamlit tab: label, render callback, and optional notebook index."""

    label: str
    render: Callable[[], None]
    notebook_index: str


DASHBOARD_TABS: tuple[DashboardTab, ...] = (
    DashboardTab(
        label="📖 00. UI Guide",
        render=guide.render,
        notebook_index="",
    ),
    DashboardTab(
        label="🚀 01. Readiness Check",
        render=readiness.render,
        notebook_index="00",
    ),
    DashboardTab(
        label="🤖 02. Complex Agent",
        render=agent.render,
        notebook_index="01",
    ),
    DashboardTab(
        label="⚖️ 03. Router & Cache",
        render=router_cache.render,
        notebook_index="02",
    ),
    DashboardTab(
        label="🏭 04. Production Queue",
        render=production.render,
        notebook_index="03",
    ),
)
