"""Shared pytest fixtures for the Streamlit demo."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import streamlit as st

DEMO_ROOT = Path(__file__).resolve().parent.parent
SHARED = DEMO_ROOT / "shared"

for path in (DEMO_ROOT, SHARED):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


@pytest.fixture
def session_state(monkeypatch):
    """Plain dict stand-in for ``st.session_state``."""
    state: dict = {}
    monkeypatch.setattr(st, "session_state", state)
    return state
