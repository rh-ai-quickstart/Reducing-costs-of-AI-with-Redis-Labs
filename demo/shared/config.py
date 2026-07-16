"""Environment and path configuration for the insurance demo."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "demo" / "notebooks" / "data"
POLICIES_PATH = DATA_DIR / "policies.json"
FAQ_PATH = DATA_DIR / "insurance_faq.json"
FAQ_INDEX_NAME = "insurance-faq"
FAQ_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _apply_model_aliases() -> None:
    api_key = os.environ.get("MODEL_API_KEY", "").strip()
    endpoint = os.environ.get("MODEL_ENDPOINT", "").strip()
    if api_key:
        os.environ.setdefault("SIMPLE_MODEL_KEY", api_key)
        os.environ.setdefault("COMPLEX_MODEL_KEY", api_key)
    if endpoint:
        os.environ.setdefault("SIMPLE_MODEL_ENDPOINT", endpoint)
        os.environ.setdefault("COMPLEX_MODEL_ENDPOINT", endpoint)


def load_config(*, reload: bool = False) -> dict:
    """Load .env from the project root and return the relevant settings."""
    load_dotenv(REPO_ROOT / ".env", override=reload)
    _apply_model_aliases()
    return {
        "simple_endpoint": os.environ["SIMPLE_MODEL_ENDPOINT"],
        "simple_key": os.environ["SIMPLE_MODEL_KEY"],
        "simple_model": os.environ.get("SIMPLE_MODEL_NAME", "qwen3-14b"),
        "complex_endpoint": os.environ["COMPLEX_MODEL_ENDPOINT"],
        "complex_key": os.environ["COMPLEX_MODEL_KEY"],
        "complex_model": os.environ.get(
            "COMPLEX_MODEL_NAME", "deepseek-r1-distill-qwen-14b"
        ),
        "redis_url": os.environ.get("REDIS_URL", "redis://localhost:6379"),
    }


def model_names(cfg: dict | None = None) -> dict[str, str]:
    """Return configured simple and complex model names for UI display."""
    cfg = cfg or load_config()
    return {
        "simple": cfg["simple_model"],
        "complex": cfg["complex_model"],
    }


def models_configured() -> bool:
    """Return True when both model endpoints and keys are set."""
    try:
        cfg = load_config()
    except KeyError:
        return False
    return all(
        [
            cfg.get("simple_endpoint"),
            cfg.get("simple_key"),
            cfg.get("complex_endpoint"),
            cfg.get("complex_key"),
        ]
    )
