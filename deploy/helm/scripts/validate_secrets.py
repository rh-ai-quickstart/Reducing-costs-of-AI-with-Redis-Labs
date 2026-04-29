#!/usr/bin/env python3
"""Merge base Helm values with values-secret.yaml and reject null/empty required fields."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        print(
            "error: PyYAML is required to validate merged Helm values.\n"
            "  python3 -m pip install pyyaml",
            file=sys.stderr,
        )
        sys.exit(2)
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Shallow-compatible merge: override keys replace base; nested dicts merge recursively."""
    out: dict[str, Any] = dict(base)
    for key, val in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def _nonempty_str(val: Any) -> bool:
    return isinstance(val, str) and bool(val.strip())


def main() -> None:
    if len(sys.argv) != 3:
        print(
            f"usage: {sys.argv[0]} <values.yaml> <values-secret.yaml>",
            file=sys.stderr,
        )
        sys.exit(2)

    base_path = Path(sys.argv[1])
    secret_path = Path(sys.argv[2])
    if not secret_path.is_file():
        print(f"error: secret file not found: {secret_path}", file=sys.stderr)
        sys.exit(1)

    merged = _deep_merge(_load_yaml(base_path), _load_yaml(secret_path))
    secrets = merged.get("secrets") or {}
    if not isinstance(secrets, dict):
        secrets = {}
    model = secrets.get("model") or {}
    if not isinstance(model, dict):
        model = {}
    redis_secret = secrets.get("redis") or {}
    if not isinstance(redis_secret, dict):
        redis_secret = {}

    errors: list[str] = []

    if not _nonempty_str(
        model.get("simpleApiKey") or not _nonempty_str(model.get("complexApiKey"))
    ):
        errors.append(
            "secrets.model.simpleApiKey and secrets.model.complexApiKey must be a non-empty string (your LLM API key)."
        )

    for key in (
        "endpoint",
        "complexModelName",
        "simpleModelName",
        "simpleEndpoint",
        "complexEndpoint",
    ):
        if not _nonempty_str(model.get(key)):
            errors.append(
                f"secrets.model.{key} must be set and non-empty "
                f'(not null, not ""); check {secret_path.name} after merge with {base_path.name}.'
            )

    redis_cfg = merged.get("redis") or {}
    if not isinstance(redis_cfg, dict):
        redis_cfg = {}
    use_ot = bool(redis_cfg.get("useOtContainerKitOperator"))
    use_enterprise = bool(redis_cfg.get("useRedisEnterpriseOperator"))
    builtin = redis_cfg.get("builtin") or {}
    builtin_on = True
    if isinstance(builtin, dict) and "enabled" in builtin:
        builtin_on = bool(builtin.get("enabled"))

    external_redis = not use_ot and not use_enterprise and not builtin_on
    if external_redis and not _nonempty_str(redis_secret.get("url")):
        errors.append(
            "With builtin Redis, the OT operator, and the Redis Enterprise operator "
            "all off, secrets.redis.url must be a non-empty redis:// or rediss:// URL."
        )

    if errors:
        print("error: secret / merged values validation failed:", file=sys.stderr)
        for msg in errors:
            print(f"  - {msg}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
