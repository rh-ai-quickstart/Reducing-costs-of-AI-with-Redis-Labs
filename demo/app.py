"""Cost-Optimized Insurance Assistant — multi-tab Streamlit demo."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

_DEMO_ROOT = Path(__file__).resolve().parent
_SHARED = _DEMO_ROOT / "shared"
for path in (_DEMO_ROOT, _SHARED):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# MaaS gateways (e.g. LiteLLM) often lack OpenAI-style tool-calling. Plain complex
# pre-fetches Redis context then uses a single chat completion. Override in .env:
# INSURANCE_PLAIN_COMPLEX=false when your complex model supports tool calls.
os.environ.setdefault("INSURANCE_PLAIN_COMPLEX", "true")
# Fresh answers are auto-stored in the semantic cache for repeat lookups.
os.environ.setdefault("INSURANCE_AUTO_CACHE", "true")

from config import load_config  # noqa: E402
from ui.registry import DASHBOARD_TABS  # noqa: E402
from ui.styles import DASHBOARD_CSS  # noqa: E402

load_config()

st.set_page_config(
    page_title="Cost-Optimized Insurance Assistant",
    layout="wide",
    page_icon="🛡️",
)
st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)

st.markdown(
    '<p class="dashboard-title">🛡️ Insurance Claims Assistant</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="dashboard-subtitle">Optimizing LLM costs using Redis + Red Hat OpenShift AI / MaaS</p>',
    unsafe_allow_html=True,
)

tabs = st.tabs([tab.label for tab in DASHBOARD_TABS])
for container, tab in zip(tabs, DASHBOARD_TABS):
    with container:
        tab.render()
