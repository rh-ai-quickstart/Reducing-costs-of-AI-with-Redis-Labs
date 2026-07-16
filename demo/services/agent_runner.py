"""Complex LangGraph agent runner with streaming for Tab 2 (complex agent)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Iterator

import insurance_bot as ib
from config import load_config
from services.pricing import ModelPricing, default_pricing, estimate_cost, format_cost


@dataclass
class AgentRunResult:
    answer: str
    model: str
    usage: dict[str, Any]
    cost_usd: float
    latency_ms: float
    tools_used: list[str] = field(default_factory=list)
    plain_complex: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def _is_tool_calling_error(exc: BaseException) -> bool:
    """Detect MaaS gateways that reject OpenAI-style tool-calling."""
    message = str(exc).lower()
    markers = (
        "tool choice",
        "tool-call",
        "tool_call",
        "auto\" tool",
        "enable-auto-tool-choice",
    )
    return any(marker in message for marker in markers)


def _run_plain_complex(cfg: dict, question: str) -> tuple[str, dict, list[str]]:
    """Single chat completion with Redis pre-fetched context (no LangGraph agent)."""
    llm = ib.build_llm("complex", cfg)
    return ib.answer_complex(llm, question)


def _run_agent(question: str, thread_id: str, cfg: dict) -> tuple[str, dict, list[str]]:
    """LangGraph ReAct agent with Redis-backed checkpointer."""
    from langgraph.checkpoint.redis import RedisSaver

    saver_cm = RedisSaver.from_conn_string(cfg["redis_url"])
    checkpointer = saver_cm.__enter__()
    try:
        checkpointer.setup()
        agent = ib.build_agent(checkpointer=checkpointer, cfg=cfg)
        result = agent.invoke(
            {"messages": [{"role": "user", "content": question}]},
            config={"configurable": {"thread_id": thread_id}},
        )
        answer = ib.strip_reasoning(result["messages"][-1].content)
        usage = ib._agent_usage(result)
        tools_used = ib.extract_tools_used(result)
        return answer, usage, tools_used
    finally:
        try:
            saver_cm.__exit__(None, None, None)
        except Exception:
            pass


def _execute_complex_path(
    question: str,
    *,
    thread_id: str,
    cfg: dict,
) -> tuple[str, dict[str, Any], list[str], bool]:
    """Run the complex model path, falling back to plain mode on tool-call errors."""
    plain_complex = ib.use_plain_complex()
    if plain_complex:
        answer, usage, tools_used = _run_plain_complex(cfg, question)
        return answer, usage, tools_used, plain_complex

    try:
        answer, usage, tools_used = _run_agent(question, thread_id, cfg)
        return answer, usage, tools_used, plain_complex
    except Exception as exc:
        if not _is_tool_calling_error(exc):
            raise
        answer, usage, tools_used = _run_plain_complex(cfg, question)
        return answer, usage, tools_used, True


def _token_chunks(text: str) -> Iterator[str]:
    """Yield whitespace-delimited tokens for simulated streaming."""
    for word in text.split(" "):
        yield word + " "


def _stream_answer_to_placeholder(
    answer: str,
    *,
    body_placeholder,
    tools_placeholder,
    tools_used: list[str],
) -> None:
    """Write the answer into Streamlit placeholders with a word-by-word effect."""
    displayed = ""
    for chunk in _token_chunks(answer):
        displayed += chunk
        body_placeholder.markdown(displayed.strip())
        time.sleep(0.015)

    if tools_used:
        tools_placeholder.markdown("\n".join(f"- `{t}`" for t in tools_used))


def run_complex_agent(
    question: str,
    *,
    thread_id: str,
    body_placeholder,
    tools_placeholder,
) -> AgentRunResult:
    """Run the complex path and stream the cleaned answer into Streamlit."""
    started = time.perf_counter()
    pricing = default_pricing()["complex"]
    cfg = load_config()
    model = cfg["complex_model"]
    plain_complex = ib.use_plain_complex()

    try:
        answer, usage, tools_used, plain_complex = _execute_complex_path(
            question,
            thread_id=thread_id,
            cfg=cfg,
        )
        _stream_answer_to_placeholder(
            answer,
            body_placeholder=body_placeholder,
            tools_placeholder=tools_placeholder,
            tools_used=tools_used,
        )

        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        cost = estimate_cost(usage, pricing)
        return AgentRunResult(
            answer=answer,
            model=model,
            usage=usage,
            cost_usd=cost,
            latency_ms=latency_ms,
            tools_used=tools_used,
            plain_complex=plain_complex,
        )
    except Exception as exc:
        body_placeholder.error(str(exc))
        return AgentRunResult(
            answer="",
            model=model,
            usage={},
            cost_usd=0.0,
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
            plain_complex=plain_complex,
            error=str(exc),
        )


def format_metrics(result: AgentRunResult, pricing: ModelPricing | None = None) -> str:
    pricing = pricing or default_pricing()["complex"]
    usage = result.usage or {}
    inp = usage.get("input_tokens", 0)
    out = usage.get("output_tokens", 0)
    total = usage.get("total_tokens", inp + out)
    tools = ", ".join(result.tools_used) if result.tools_used else "none"
    mode = (
        "Redis pre-fetch + chat completion (MaaS-safe)"
        if result.plain_complex
        else "LangGraph tool-calling agent"
    )
    return (
        f"**Model:** {result.model}\n\n"
        f"**Mode:** {mode}\n\n"
        f"**Latency:** {result.latency_ms:.0f} ms\n\n"
        f"**Tokens:** {total:,} (in {inp:,} / out {out:,})\n\n"
        f"**Est. cost:** {format_cost(result.cost_usd)}\n\n"
        f"**Redis tools:** {tools}"
    )
