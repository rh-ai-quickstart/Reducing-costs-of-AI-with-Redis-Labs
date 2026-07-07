"""Streamlit UI package."""

from ui.registry import DASHBOARD_TABS, DashboardTab
from ui.tabs import agent, production, readiness, router_cache

__all__ = [
    "DASHBOARD_TABS",
    "DashboardTab",
    "agent",
    "production",
    "readiness",
    "router_cache",
]
