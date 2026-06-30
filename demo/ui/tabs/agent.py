"""Tab 1 — Complex baseline agent (always-expensive path)."""

from __future__ import annotations

import streamlit as st

from config import model_names
from services.agent_runner import format_metrics, run_complex_agent
from ui.components import QuestionPickerConfig, render_question_picker
from ui.state import AgentTabState

EXAMPLE_QUESTIONS = [
    "My car was flooded in a storm, is my rental covered while it's in the shop?",
    "What documents do I need to file an auto claim?",
    "How does my deductible work on policy AUTO-1001?",
    "A tree fell on my roof during the storm, how do I start a claim?",
]

_QUESTION_PICKER = QuestionPickerConfig(
    example_label="Example complex questions",
    example_key="t1_example",
    query_label="Your question",
    query_key="t1_query",
    ask_button_label="Ask Agent",
    ask_button_key="t1_ask",
)


def _render_chat_column() -> None:
    """Collect user input and run the complex agent when requested."""
    submitted = render_question_picker(EXAMPLE_QUESTIONS, _QUESTION_PICKER)
    if submitted:
        AgentTabState.start_run(submitted)

    question = AgentTabState.pending_question()
    if not question:
        return

    st.chat_message("user").write(question)
    with st.chat_message("assistant"):
        body = st.empty()
        tools_box = st.empty()
        with st.spinner("Agent thinking..."):
            result = run_complex_agent(
                question,
                thread_id="ui-tab1-agent",
                body_placeholder=body,
                tools_placeholder=tools_box,
            )
        AgentTabState.finish_run(result)


def _render_metrics_column() -> None:
    """Show token/cost metrics for the most recent agent run."""
    st.subheader("⚡ Under the Hood")
    result = AgentTabState.last_result()

    if result and result.ok:
        st.markdown(format_metrics(result))
        if result.tools_used:
            st.markdown("**Vector Search tools triggered:**")
            for tool in result.tools_used:
                st.code(tool, language=None)
        return

    if result and result.error:
        st.error(result.error)
        return

    st.info(
        f"Model: **{model_names()['complex']}**\n\n"
        "Metrics appear after you ask a question."
    )


def render() -> None:
    complex_model = model_names()["complex"]
    st.header("The Baseline: Complex Reasoning Agent")
    st.caption(
        f"Every question hits {complex_model} + Redis Vector Search. "
        "Powerful, but slow and expensive."
    )

    col_chat, col_metrics = st.columns([2, 1])
    with col_chat:
        _render_chat_column()
    with col_metrics:
        _render_metrics_column()
