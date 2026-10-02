"""Tests for streaming chat helpers in insurance_bot."""

from __future__ import annotations

from types import SimpleNamespace

import insurance_bot as ib


class _FakeLLM:
    def __init__(self, chunks: list):
        self._chunks = chunks

    def stream(self, messages):
        yield from self._chunks


def test_visible_stream_text_hides_incomplete_think():
    assert ib.visible_stream_text("Hi <think>secret") == "Hi"


def test_visible_stream_text_strips_complete_think():
    assert ib.visible_stream_text("Before <think>hidden</think> After") == "Before  After"


def test_stream_chat_joins_chunks_strips_think_and_keeps_usage():
    chunks = [
        SimpleNamespace(content="<think>plan", usage_metadata=None),
        SimpleNamespace(content="ning</think>Final", usage_metadata=None),
        SimpleNamespace(
            content=" answer",
            usage_metadata={"input_tokens": 10, "output_tokens": 3, "total_tokens": 13},
        ),
    ]
    seen: list[str] = []
    text, usage = ib.stream_chat(
        _FakeLLM(chunks),
        [{"role": "user", "content": "q"}],
        on_token=seen.append,
    )
    assert text == "Final answer"
    assert usage == {"input_tokens": 10, "output_tokens": 3, "total_tokens": 13}
    assert seen[-1] == "Final answer"
    assert all("<think>" not in piece.lower() for piece in seen)
    assert all("</think>" not in piece.lower() for piece in seen)


def test_stream_chat_handles_list_content_blocks():
    chunks = [
        SimpleNamespace(
            content=[{"type": "text", "text": "Hello "}, {"type": "text", "text": "world"}],
            usage_metadata={"input_tokens": 1, "output_tokens": 2, "total_tokens": 3},
        )
    ]
    text, usage = ib.stream_chat(_FakeLLM(chunks), [{"role": "user", "content": "q"}])
    assert text == "Hello world"
    assert usage["total_tokens"] == 3
