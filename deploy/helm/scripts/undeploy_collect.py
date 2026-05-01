#!/usr/bin/env python3
"""Run helm uninstall + OLM cleanup; append NDJSON debug lines (no secrets)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

# #region agent log
# deploy/helm/scripts -> repo root is parents[3]
DEBUG_LOG = Path(__file__).resolve().parents[3] / ".cursor" / "debug-a9baac.log"
SESSION_ID = "a9baac"


def _log(hypothesis_id: str, message: str, data: dict) -> None:
    rec = {
        "sessionId": SESSION_ID,
        "timestamp": int(time.time() * 1000),
        "hypothesisId": hypothesis_id,
        "message": message,
        "data": data,
    }
    DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
    with DEBUG_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, default=str) + "\n")


# #endregion


def _run(
    cmd: list[str],
    *,
    hypothesis_id: str,
    log_label: str,
    timeout: int = 600,
) -> subprocess.CompletedProcess[str]:
    _log(
        hypothesis_id,
        f"run:{log_label}",
        {"cmd": cmd},
    )
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        _log(
            hypothesis_id,
            f"timeout:{log_label}",
            {"cmd": cmd, "error": str(e)},
        )
        raise
    _log(
        hypothesis_id,
        f"result:{log_label}",
        {
            "returncode": p.returncode,
            "stderr_tail": (p.stderr or "")[-2000:],
            "stdout_tail": (p.stdout or "")[-2000:],
        },
    )
    return p


def _subs_snapshot(kubectl: str, hypothesis_id: str, message: str) -> None:
    # All namespaces: find redis-enterprise / redislabs subscriptions (H1, H4)
    p = _run(
        [
            kubectl,
            "get",
            "subscriptions.operators.coreos.com",
            "-A",
            "-o",
            "json",
        ],
        hypothesis_id=hypothesis_id,
        log_label="subs_all_namespaces",
        timeout=120,
    )
    items: list[dict] = []
    try:
        doc = json.loads(p.stdout or "{}")
        for it in doc.get("items") or []:
            md = it.get("metadata") or {}
            spec = it.get("spec") or {}
            name = md.get("name", "")
            ns = md.get("namespace", "")
            labels = md.get("labels") or {}
            pkg = spec.get("name", "")
            if "redis" in (name + pkg).lower() or "redislabs" in (name + pkg).lower():
                items.append(
                    {
                        "name": name,
                        "namespace": ns,
                        "spec_name": pkg,
                        "labels": {
                            k: labels.get(k)
                            for k in (
                                "app.kubernetes.io/instance",
                                "app.kubernetes.io/managed-by",
                                "app.kubernetes.io/component",
                            )
                            if k in labels
                        },
                    }
                )
    except json.JSONDecodeError as e:
        _log(hypothesis_id, "subs_json_error", {"error": str(e)})
        return
    _log(hypothesis_id, message, {"redis_related_subscriptions": items[:50]})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--helm-release", required=True)
    ap.add_argument("--namespace", required=True)
    ap.add_argument("--ai-operator-ns", required=True)
    ap.add_argument("--kubectl", required=True)
    args = ap.parse_args()
    kubectl = args.kubectl
    ns = args.namespace
    rel = args.helm_release
    ai_ns = args.ai_operator_ns

    _log("H0", "undeploy_collect_start", {"release": rel, "namespace": ns, "ai_ns": ai_ns})

    # H5: release present?
    p_list = _run(
        ["helm", "list", "-n", ns, "-o", "json"],
        hypothesis_id="H5",
        log_label="helm_list",
        timeout=60,
    )
    _log("H5", "helm_list_parsed", {"raw_tail": (p_list.stdout or "")[:4000]})

    # H2/H4: subscriptions in release namespace (full json subset)
    p_ns = _run(
        [
            kubectl,
            "get",
            "subscriptions.operators.coreos.com",
            "-n",
            ns,
            "-o",
            "json",
        ],
        hypothesis_id="H4",
        log_label="subs_release_ns",
        timeout=60,
    )
    try:
        doc = json.loads(p_ns.stdout or "{}")
        subs = []
        for it in doc.get("items") or []:
            md = it.get("metadata") or {}
            subs.append(
                {
                    "name": md.get("name"),
                    "labels": md.get("labels") or {},
                }
            )
        _log("H4", "subscriptions_in_release_ns", {"namespace": ns, "items": subs})
    except json.JSONDecodeError as e:
        _log("H4", "subs_release_ns_json_error", {"error": str(e)})

    _subs_snapshot(kubectl, "H1", "redis_like_subscriptions_all_ns_before")

    # Helm uninstall (continue cleanup even if release missing / helm errors)
    p_un = _run(
        ["helm", "uninstall", rel, "--namespace", ns, "--wait"],
        hypothesis_id="H5",
        log_label="helm_uninstall",
        timeout=600,
    )
    if p_un.returncode != 0:
        _log(
            "H5",
            "helm_uninstall_nonzero",
            {"returncode": p_un.returncode, "note": "continuing_with_olm_cleanup"},
        )

    _subs_snapshot(kubectl, "H1", "redis_like_subscriptions_all_ns_after_helm_uninstall")

    # Label-based cleanup (same as Makefile)
    selector_redis = f"app.kubernetes.io/instance={rel},app.kubernetes.io/managed-by=Helm,app.kubernetes.io/component=redis-enterprise-olm"
    selector_ai = f"app.kubernetes.io/instance={rel},app.kubernetes.io/managed-by=Helm,app.kubernetes.io/component=openshift-ai-operator"

    for kind, sel, n in (
        ("subscriptions.operators.coreos.com", selector_redis, ns),
        ("operatorgroups.operators.coreos.com", selector_redis, ns),
        ("subscriptions.operators.coreos.com", selector_ai, ai_ns),
        ("operatorgroups.operators.coreos.com", selector_ai, ai_ns),
    ):
        _run(
            [kubectl, "delete", kind, "-n", n, "-l", sel, "--ignore-not-found"],
            hypothesis_id="H3",
            log_label=f"delete_{kind}_{n}",
            timeout=120,
        )

    _subs_snapshot(kubectl, "H1", "redis_like_subscriptions_all_ns_after_kubectl_delete")

    _log("H0", "undeploy_collect_done", {})


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _log("H0", "undeploy_collect_fatal", {"error": type(e).__name__, "message": str(e)})
        sys.exit(1)
