"""Token pricing and cost estimation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from config import load_config

# Rough character overhead mirrored from the complex / plain-complex path.
_COMPLEX_SYSTEM_AND_RAG_CHARS = 2000
_SIMPLE_SYSTEM_CHARS = 350
# Floor for a substantive complex-model claims answer (not a one-line refusal).
_COMPLEX_OUTPUT_TOKEN_FLOOR = 120


@dataclass(frozen=True)
class ModelPricing:
    label: str
    display_name: str
    input_per_million: float
    output_per_million: float


def _float_env(key: str, default: float) -> float:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def default_pricing() -> dict[str, ModelPricing]:
    cfg = load_config()
    return {
        "simple": ModelPricing(
            label="simple",
            display_name=cfg["simple_model"],
            input_per_million=_float_env("ROI_SIMPLE_INPUT_COST_PER_MILLION", 0.15),
            output_per_million=_float_env("ROI_SIMPLE_OUTPUT_COST_PER_MILLION", 0.60),
        ),
        "complex": ModelPricing(
            label="complex",
            display_name=cfg["complex_model"],
            input_per_million=_float_env("ROI_COMPLEX_INPUT_COST_PER_MILLION", 2.50),
            output_per_million=_float_env("ROI_COMPLEX_OUTPUT_COST_PER_MILLION", 10.00),
        ),
    }


def coerce_usage(raw: Any) -> dict[str, Any]:
    """Normalize LangChain/OpenAI usage payloads to a plain dict."""
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    if hasattr(raw, "get"):
        try:
            return dict(raw)
        except Exception:
            pass
    return {
        "input_tokens": getattr(raw, "input_tokens", None)
        or getattr(raw, "prompt_tokens", None)
        or 0,
        "output_tokens": getattr(raw, "output_tokens", None)
        or getattr(raw, "completion_tokens", None)
        or 0,
        "total_tokens": getattr(raw, "total_tokens", None) or 0,
    }


def estimate_cost(usage: dict[str, Any], pricing: ModelPricing) -> float:
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    input_cost = (input_tokens / 1_000_000) * pricing.input_per_million
    output_cost = (output_tokens / 1_000_000) * pricing.output_per_million
    return input_cost + output_cost


def format_cost(amount: float) -> str:
    if amount <= 0:
        return "$0.00"
    if amount < 0.01:
        return f"${amount:.6f}"
    return f"${amount:.4f}"


def _tokenize_chars(char_count: int, minimum: int) -> int:
    return max(minimum, char_count // 4)


def normalize_usage(
    usage: dict[str, Any] | None,
    *,
    question: str,
    answer: str = "",
    system_chars: int = _SIMPLE_SYSTEM_CHARS,
    output_floor: int = 20,
) -> tuple[dict[str, int], bool]:
    """Return token counts for the path that actually ran; True if estimated."""
    raw = coerce_usage(usage)
    inp = int(raw.get("input_tokens") or raw.get("prompt_tokens") or 0)
    out = int(raw.get("output_tokens") or raw.get("completion_tokens") or 0)
    estimated = False

    if inp == 0 and out == 0:
        estimated = True
        inp = _tokenize_chars(len(question) + system_chars, 50)
        out = _tokenize_chars(len(answer), output_floor) if answer else output_floor

    total = int(raw.get("total_tokens") or inp + out)
    return {"input_tokens": inp, "output_tokens": out, "total_tokens": total}, estimated


def baseline_complex_usage(question: str, answer: str = "") -> dict[str, int]:
    """Counterfactual tokens if this question had gone through the complex agent."""
    inp = _tokenize_chars(len(question) + _COMPLEX_SYSTEM_AND_RAG_CHARS, 250)
    observed_out = _tokenize_chars(len(answer), 0) if answer else 0
    out = max(_COMPLEX_OUTPUT_TOKEN_FLOOR, observed_out)
    return {"input_tokens": inp, "output_tokens": out, "total_tokens": inp + out}


def actual_usage_for_outcome(outcome: dict[str, Any], question: str, answer: str) -> tuple[dict[str, int], bool]:
    """Token counts for what the pipeline actually executed."""
    route = outcome.get("route")
    cached = bool(outcome.get("cached"))
    raw_usage = outcome.get("usage")

    if route == "blocked" or cached:
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}, False

    if route == "simple":
        return normalize_usage(
            raw_usage,
            question=question,
            answer=answer,
            system_chars=_SIMPLE_SYSTEM_CHARS,
            output_floor=20,
        )

    if route == "complex":
        return normalize_usage(
            raw_usage,
            question=question,
            answer=answer,
            system_chars=_COMPLEX_SYSTEM_AND_RAG_CHARS,
            output_floor=_COMPLEX_OUTPUT_TOKEN_FLOOR,
        )

    return normalize_usage(raw_usage, question=question, answer=answer)


def baseline_complex_cost(usage: dict[str, int]) -> float:
    """Price a token profile at complex-model rates."""
    return estimate_cost(usage, default_pricing()["complex"])
