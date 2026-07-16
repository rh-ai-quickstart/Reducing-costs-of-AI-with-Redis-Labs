"""Shared preset + free-text question input used by Tabs 2 and 3."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class QuestionPickerConfig:
    """Streamlit widget keys and labels for a question picker block."""

    example_label: str
    example_key: str
    query_label: str
    query_key: str
    ask_button_label: str
    ask_button_key: str
    custom_option: str = "— type your own —"
    example_help: str = ""
    query_help: str = ""
    ask_button_help: str = ""


def render_question_picker(
    examples: list[str],
    config: QuestionPickerConfig,
) -> str:
    """Render example selectbox, text input, and ask button; return trimmed query."""
    example = st.selectbox(
        config.example_label,
        options=[config.custom_option, *examples],
        key=config.example_key,
        help=config.example_help or None,
    )
    default_q = examples[0] if examples else ""
    if example != config.custom_option:
        default_q = example

    user_query = st.text_input(
        config.query_label,
        value=default_q,
        key=config.query_key,
        help=config.query_help or None,
    )

    if st.button(
        config.ask_button_label,
        type="primary",
        key=config.ask_button_key,
        help=config.ask_button_help or None,
    ):
        return user_query.strip()

    return ""
