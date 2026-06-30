"""Cost analysis helpers for the router & cache tab."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.pricing import (
    actual_usage_for_outcome,
    baseline_complex_cost,
    baseline_complex_usage,
    default_pricing,
    estimate_cost,
)


@dataclass
class RequestCostSnapshot:
    question: str
    route: str
    cached: bool
    path_label: str
    model: str | None
    actual_cost: float
    baseline_cost: float
    saved: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    baseline_input_tokens: int = 0
    baseline_output_tokens: int = 0
    baseline_total_tokens: int = 0
    latency_ms: float | None = None
    tokens_estimated: bool = False
    baseline_estimated: bool = True

    @property
    def savings_pct(self) -> float:
        if self.baseline_cost <= 0:
            return 0.0
        return min(100.0, (self.saved / self.baseline_cost) * 100.0)


@dataclass
class SessionCostTotals:
    request_count: int = 0
    actual_spend: float = 0.0
    baseline_spend: float = 0.0
    total_saved: float = 0.0
    simple_count: int = 0
    blocked_count: int = 0
    cache_hit_count: int = 0
    complex_count: int = 0
    history: list[RequestCostSnapshot] = field(default_factory=list)


def _path_label(outcome: dict[str, Any]) -> str:
    route = outcome.get("route")
    if route == "blocked":
        return "Router → Blocked"
    if route == "simple":
        return "Router → Simple model"
    if outcome.get("cached"):
        return "Cache hit"
    if route == "complex":
        return "Cache miss → Agent"
    return route or "unknown"


def snapshot_from_outcome(question: str, outcome: dict[str, Any]) -> RequestCostSnapshot:
    pricing = default_pricing()
    answer = str(outcome.get("answer") or "")
    route = outcome.get("route")
    cached = bool(outcome.get("cached"))

    actual_usage, tokens_estimated = actual_usage_for_outcome(outcome, question, answer)
    baseline_usage = baseline_complex_usage(question, answer)

    if route == "blocked" or cached:
        actual = 0.0
        model = None
    elif route == "simple":
        actual = estimate_cost(actual_usage, pricing["simple"])
        model = outcome.get("model")
    elif route == "complex":
        actual = estimate_cost(actual_usage, pricing["complex"])
        model = outcome.get("model")
    else:
        actual = 0.0
        model = outcome.get("model")

    baseline = baseline_complex_cost(baseline_usage)
    if route == "complex" and not cached:
        # Observed complex bill is the true always-complex cost for this question.
        baseline = max(baseline, actual)
        baseline_usage = {
            "input_tokens": max(baseline_usage["input_tokens"], actual_usage["input_tokens"]),
            "output_tokens": max(baseline_usage["output_tokens"], actual_usage["output_tokens"]),
            "total_tokens": max(baseline_usage["total_tokens"], actual_usage["total_tokens"]),
        }

    saved = max(0.0, baseline - actual)

    return RequestCostSnapshot(
        question=question,
        route=str(route or ""),
        cached=cached,
        path_label=_path_label(outcome),
        model=model,
        actual_cost=actual,
        baseline_cost=baseline,
        saved=saved,
        input_tokens=actual_usage["input_tokens"],
        output_tokens=actual_usage["output_tokens"],
        total_tokens=actual_usage["total_tokens"],
        baseline_input_tokens=baseline_usage["input_tokens"],
        baseline_output_tokens=baseline_usage["output_tokens"],
        baseline_total_tokens=baseline_usage["total_tokens"],
        latency_ms=outcome.get("latency_ms"),
        tokens_estimated=tokens_estimated,
        baseline_estimated=True,
    )


def record_request(totals: SessionCostTotals, snap: RequestCostSnapshot) -> None:
    totals.request_count += 1
    totals.actual_spend += snap.actual_cost
    totals.baseline_spend += snap.baseline_cost
    totals.total_saved += snap.saved
    if snap.route == "simple":
        totals.simple_count += 1
    elif snap.route == "blocked":
        totals.blocked_count += 1
    elif snap.cached:
        totals.cache_hit_count += 1
    elif snap.route == "complex":
        totals.complex_count += 1
    totals.history.append(snap)


def empty_totals() -> SessionCostTotals:
    return SessionCostTotals()
