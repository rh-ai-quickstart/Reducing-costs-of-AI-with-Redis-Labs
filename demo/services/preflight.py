"""Infrastructure preflight checks for Tab 1 (readiness).

Validates Redis, MaaS model endpoints, and the RAK insurance worker before the
demo UI runs live requests.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from config import load_config
from shared.utils.openai_utils import openai_base_url


@dataclass
class CheckResult:
    """Outcome of a single infrastructure check."""

    name: str
    status: str
    detail: str
    latency_ms: float | None = None

    @property
    def ok(self) -> bool:
        return self.status in {"connected", "ready", "healthy"}


def status_label(result: CheckResult) -> str:
    """Human-readable status line for UI cards."""
    if result.ok:
        return "🟢 Connected"
    if result.status == "idle":
        return "🟡 Not running"
    if result.status in {"degraded", "missing", "empty"}:
        return "🟡 Degraded"
    return "🔴 Failed"


def _status_badge(status: str) -> str:
    """Compact emoji badge for summary views."""
    if status in {"connected", "ready", "healthy"}:
        return "🟢"
    if status in {"degraded", "missing", "empty", "idle"}:
        return "🟡"
    return "🔴"


def check_redis() -> CheckResult:
    """Ping Redis and report server version."""
    cfg = load_config()
    started = time.perf_counter()
    try:
        from redis import Redis

        client = Redis.from_url(cfg["redis_url"], socket_connect_timeout=5)
        pong = client.ping()
        info = client.info(section="server")
        version = info.get("redis_version") or info.get("valkey_version", "?")
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        status = "connected" if pong else "degraded"
        return CheckResult(
            name="Redis",
            status=status,
            detail=f"v{version} · PING={pong}",
            latency_ms=latency_ms,
        )
    except Exception as exc:
        return CheckResult(
            name="Redis",
            status="failed",
            detail=f"{type(exc).__name__}: {exc}",
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
        )


def check_model(which: str) -> CheckResult:
    """Send a one-token probe to the simple or complex MaaS endpoint."""
    cfg = load_config()
    model = cfg[f"{which}_model"]
    label = f"MaaS {which.title()} Model ({model})"
    started = time.perf_counter()
    try:
        from openai import OpenAI

        client = OpenAI(
            base_url=openai_base_url(cfg[f"{which}_endpoint"]),
            api_key=cfg[f"{which}_key"],
            timeout=15.0,
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        return CheckResult(
            name=label,
            status="ready",
            detail=f"{model} responsive (id={resp.id[:12]}…)",
            latency_ms=latency_ms,
        )
    except Exception as exc:
        return CheckResult(
            name=label,
            status="failed",
            detail=f"{type(exc).__name__}: {exc}",
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
        )


def check_rak_worker() -> CheckResult:
    """Verify the Redis Streams queue and RAK worker consumer group."""
    from services.queue_client import QUEUE_NAME, redis_stream_metrics

    started = time.perf_counter()
    metrics = redis_stream_metrics()
    latency_ms = round((time.perf_counter() - started) * 1000, 1)

    if metrics.get("error"):
        return CheckResult(
            name="RAK Insurance Worker",
            status="failed",
            detail=metrics["error"],
            latency_ms=latency_ms,
        )

    workers = int(metrics.get("active_workers") or 0)
    stream_key = metrics.get("stream_key") or f"docket:{QUEUE_NAME}:stream"
    queue_depth = metrics.get("queue_length", 0)

    if workers > 0:
        return CheckResult(
            name="RAK Insurance Worker",
            status="ready",
            detail=f"{workers} consumer(s) on {stream_key} · depth={queue_depth}",
            latency_ms=latency_ms,
        )

    return CheckResult(
        name="RAK Insurance Worker",
        status="idle",
        detail=(
            f"No active consumers on {stream_key} · depth={queue_depth}. "
            "Deploy insuranceWorker or run `rak worker --tasks insurance_worker:tasks`."
        ),
        latency_ms=latency_ms,
    )


def run_preflight_checks() -> list[CheckResult]:
    """Run all Tab 1 (readiness) infrastructure checks."""
    return [
        check_redis(),
        check_model("simple"),
        check_model("complex"),
        check_rak_worker(),
    ]


def checks_summary(results: list[CheckResult]) -> dict[str, Any]:
    """Aggregate check results for dashboard badges."""
    return {
        "all_ok": all(r.ok for r in results),
        "results": results,
        "badges": {r.name: _status_badge(r.status) for r in results},
    }
