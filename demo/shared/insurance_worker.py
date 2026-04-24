"""Redis Agent Kit worker module for the insurance pipeline.

Exposes a ``tasks`` list consumable by ``rak worker --tasks insurance_worker:tasks``.
The shared :class:`InsurancePipeline` is lazily built inside the worker process
so that module import stays cheap for the submitting side.
"""

from __future__ import annotations

import asyncio
from typing import Any

from redis_agent_kit import AgentKit, EmitterMiddleware, TaskContext

import insurance_bot as ib

QUEUE_NAME = "insurance"

_pipeline: ib.InsurancePipeline | None = None
_pipeline_lock = asyncio.Lock()


async def _get_pipeline() -> ib.InsurancePipeline:
    """Lazily build a single pipeline per worker process."""
    global _pipeline
    async with _pipeline_lock:
        if _pipeline is None:
            loop = asyncio.get_running_loop()
            _pipeline = await loop.run_in_executor(None, ib.build_pipeline)
    return _pipeline


async def run_agent(ctx: TaskContext) -> dict[str, Any]:
    """RAK task handler that routes an insurance question through the pipeline."""
    await ctx.emitter.emit("Classifying question...")

    pipeline = await _get_pipeline()
    thread_id = ctx.session_id or "rak-worker"

    await ctx.emitter.emit("Dispatching to router...")
    loop = asyncio.get_running_loop()
    outcome = await loop.run_in_executor(
        None, lambda: pipeline.handle(ctx.message, thread_id)
    )

    await ctx.emitter.emit(f"route={outcome['route']} cached={outcome['cached']}")
    return {
        "response": outcome["answer"],
        "route": outcome["route"],
        "model": outcome["model"],
        "cached": outcome["cached"],
        "usage": outcome.get("usage", {}),
    }


cfg = ib.load_config()

kit = AgentKit(
    redis_url=cfg["redis_url"],
    agent_callable=run_agent,
    middleware=[EmitterMiddleware(start_message="Insurance worker starting...")],
    queue_name=QUEUE_NAME,
)

tasks = [kit.worker_task]
