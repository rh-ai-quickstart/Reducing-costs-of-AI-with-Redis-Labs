"""Shared agent factories for the insurance-claims demo.

Exposes the LangGraph agent plumbing used by ``02_router_cache.ipynb``. The
agent setup is duplicated inline in ``01_agent.ipynb`` as a step-by-step
walkthrough; this module is the re-usable version notebook 02 imports.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "demo" / "notebooks" / "data"
POLICIES_PATH = DATA_DIR / "policies.json"
FAQ_PATH = DATA_DIR / "insurance_faq.json"

AGENT_SYSTEM_PROMPT = (
    "You are an insurance claims assistant. "
    "Use the provided tools to look up FAQ guidance, policy details, and "
    "required documents before answering. "
    "Ground every answer in tool output. If a tool returns nothing relevant, "
    "say so plainly. Do not speculate about claim status, payouts, or "
    "adjuster assignments."
)


def load_config() -> dict:
    """Load .env from the project root and return the relevant settings."""
    load_dotenv(REPO_ROOT / ".env")
    return {
        "api_key": os.environ["MODEL_API_KEY"],
        "endpoint": os.environ.get("MODEL_ENDPOINT", "https://api.openai.com"),
        "simple_model": os.environ.get("SIMPLE_MODEL_NAME", "gpt-4.1"),
        "complex_model": os.environ.get("COMPLEX_MODEL_NAME", "gpt-5"),
        "redis_url": os.environ.get("REDIS_URL", "redis://localhost:6379"),
    }


@lru_cache(maxsize=1)
def load_policies() -> dict:
    with open(POLICIES_PATH) as f:
        return {p["policy_id"]: p for p in json.load(f)}


@lru_cache(maxsize=1)
def load_faq() -> list[dict]:
    with open(FAQ_PATH) as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _faq_embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("all-MiniLM-L6-v2")


@lru_cache(maxsize=1)
def _faq_embeddings():
    import numpy as np

    model = _faq_embedder()
    texts = [item["question"] for item in load_faq()]
    return np.asarray(model.encode(texts, normalize_embeddings=True))


def _search_faq(query: str, k: int = 3) -> list[dict]:
    import numpy as np

    q = _faq_embedder().encode([query], normalize_embeddings=True)
    scores = (_faq_embeddings() @ q.T).ravel()
    top = np.argsort(-scores)[:k]
    faq = load_faq()
    return [
        {
            "question": faq[i]["question"],
            "answer": faq[i]["answer"],
            "category": faq[i]["category"],
            "score": float(scores[i]),
        }
        for i in top
    ]


def build_tools():
    """Return the LangChain tools the agent can call."""
    from langchain_core.tools import tool

    @tool
    def search_faq(query: str) -> list[dict]:
        """Search insurance FAQ guidance. Returns top matches with answer text."""
        return _search_faq(query, k=3)

    @tool
    def get_policy_details(policy_id: str) -> dict:
        """Look up a policy by id (e.g. 'AUTO-1001'). Returns coverages and deductibles."""
        policies = load_policies()
        if policy_id not in policies:
            return {
                "error": f"policy {policy_id} not found",
                "known_ids": list(policies.keys()),
            }
        return policies[policy_id]

    @tool
    def list_required_documents(claim_type: str) -> list[str]:
        """List typical documents needed for a claim type (e.g. 'auto', 'windshield', 'homeowners')."""
        catalog = {
            "auto": [
                "date and location of incident",
                "policy number",
                "photos of damage",
                "incident description",
                "police or incident report number",
            ],
            "windshield": [
                "photos of the damaged glass",
                "policy number",
                "date of damage",
            ],
            "homeowners": [
                "photos of damage",
                "policy number",
                "description of what happened",
                "repair estimates",
                "receipts for temporary repairs",
            ],
        }
        return catalog.get(
            claim_type.lower(),
            [
                "policy number",
                "date and description of incident",
                "any photos or receipts related to the loss",
            ],
        )

    return [search_faq, get_policy_details, list_required_documents]


def build_llm(model_name: str, cfg: dict | None = None):
    from langchain_openai import ChatOpenAI

    cfg = cfg or load_config()
    return ChatOpenAI(
        model=model_name,
        api_key=cfg["api_key"],
        base_url=f"{cfg['endpoint'].rstrip('/')}/v1",
    )


def build_agent(checkpointer=None, cfg: dict | None = None):
    """LangGraph ReAct agent that handles complex claims questions."""
    from langgraph.prebuilt import create_react_agent

    cfg = cfg or load_config()
    llm = build_llm(cfg["complex_model"], cfg)
    return create_react_agent(
        model=llm,
        tools=build_tools(),
        checkpointer=checkpointer,
        prompt=AGENT_SYSTEM_PROMPT,
    )


def agent_answer(agent, question: str, thread_id: str = "demo-thread") -> str:
    """Invoke the LangGraph agent and return the final assistant message."""
    config = {"configurable": {"thread_id": thread_id}}
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]}, config=config
    )
    return result["messages"][-1].content
