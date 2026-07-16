# Streamlit demo UI — tab guide

The dashboard has five tabs. 
**Tab 0** renders **[`docs/embeded_guide.md`](embeded_guide.md)** in the UI — no cluster calls, just documentation.
**Tabs 1–4** run four interactive scenarios in order: 

- Tab 1 validates the all infrastructure is up and running.
- Tab 2 shows the expensive models performance and cost.
- Tab 3 intercepts traffic before it reaches the complex model
- Tab 4 hands work off to background workers so the UI stays responsive under load.

---

## Getting started

You reach the same UI two ways: **run Streamlit on your laptop** (fastest for development) or **open the Route after Helm deploy on OpenShift** (conference / cluster demo). Both paths need Redis, model API credentials, and — for Tab 4 — a RAK worker.

### Option A — Run locally

**1. Prerequisites**

- Python 3.11+ and a virtualenv
- **Redis** at `REDIS_URL` (default `redis://localhost:6379`). Use **Redis Stack** or **Redis Enterprise** — the router and cache need search modules.
- An OpenAI-compatible API key and endpoint (OpenAI, OpenShift AI MaaS, LiteLLM, etc.)

**2. Configure environment**

From the repository root, create `.env`:

```dotenv
MODEL_API_KEY=sk-...
MODEL_ENDPOINT=https://api.openai.com
SIMPLE_MODEL_NAME=gpt-4.1
COMPLEX_MODEL_NAME=gpt-5
REDIS_URL=redis://localhost:6379
```

**3. Install and start the UI**

```bash
cd demo
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt --extra-index-url https://pypi.org/simple
streamlit run app.py
```

Streamlit prints a local URL (typically **http://localhost:8501**). Open it in your browser — you should see **Insurance Claims Assistant** with five tabs across the top.

**4. Optional — Tab 4 worker locally**

Tab 4 enqueues to Redis Streams; something must consume the queue:

```bash
# In a second terminal, from demo/ with the same venv and .env
rak worker --name insurance --tasks insurance_worker:tasks --concurrency 4
```

Without a worker, Tabs 0–3 still work; Tab 4 tasks will sit in the queue.

---

### Option B — OpenShift (Helm)

**1. Prerequisites**

- OpenShift cluster with `oc` and `helm` configured
- **`deploy/helm/values-secret.yaml`** — copy from `values-secret.example.yaml` and set at least `secrets.model.apiKey`
- Redis Enterprise operator in the target namespace (or use external Redis — see [deploy/README.md](../deploy/README.md))

The chart enables the dashboard by default (`roiDashboard.enabled: true`).

**2. Deploy**

```bash
cp deploy/helm/values-secret.example.yaml deploy/helm/values-secret.yaml
# Edit deploy/helm/values-secret.yaml

make -f deploy/helm/Makefile deploy
```

A plain `make deploy` installs the notebook, Redis, **Streamlit dashboard**, and **insurance RAK worker** (for Tab 4). Wait for pods to become Ready:

```bash
oc rollout status deployment -n redis-notebook -l app.kubernetes.io/component=roi-dashboard
oc rollout status deployment -n redis-notebook -l app.kubernetes.io/component=insurance-worker
```

**3. Get the URL**

```bash
make -f deploy/helm/Makefile route-roi-dashboard NAMESPACE=redis-notebook
```

Or:

```bash
oc get route -n redis-notebook -l app.kubernetes.io/component=roi-dashboard \
  -o jsonpath='https://{.items[0].spec.host}{"\n"}'
```

Open that HTTPS URL in your browser. The pod runs `streamlit run demo/app.py` on port 8501 behind an OpenShift Route with edge TLS.

If no Route exists (or you are off-cluster), port-forward instead:

```bash
oc port-forward -n redis-notebook svc/redis-notebook-roi-dashboard 8501:8501
# Then open http://localhost:8501
```

**4. Deploying from a fork or feature branch**

Until your branch is on the default git-sync repo, point Helm at your fork:

```bash
make -f deploy/helm/Makefile deploy \
  HELM_EXTRA_ARGS='--set roiDashboard.gitSync.repo=https://github.com/YOUR_ORG/Reducing-costs-of-AI-with-Redis-Labs.git --set roiDashboard.gitSync.branch=YOUR_BRANCH'
```

**5. Troubleshooting reachability**

| Symptom | What to check |
|---------|----------------|
| Route 404 or connection refused | `make -f deploy/helm/Makefile logs-roi-dashboard NAMESPACE=redis-notebook` — pod may still be installing deps at startup |
| Blank page / import errors | `make -f deploy/helm/Makefile logs-roi-clone NAMESPACE=redis-notebook` — git-sync may have failed to copy `demo/` |
| Models fail on Tab 2+ | Secrets not injected — verify `values-secret.yaml` and redeploy |
| Tab 4 stuck on PENDING | Worker pod not running — `make -f deploy/helm/Makefile logs-insurance-worker NAMESPACE=redis-notebook` |

---

### First steps in the UI

Once the page loads:

1. Skim **📖 00. UI Guide** (this document) or continue below for the full walkthrough.
2. Open **🚀 01. Readiness Check** and click **Run Preflight Checks**. Fix anything red before spending tokens.
3. Work through tabs **02 → 03 → 04** in order — each builds on the previous scenario.

More detail on what each tab does: sections below.

---

## How the tabs connect

```mermaid
flowchart LR
  T0[00 UI Guide] --> T1[01 Readiness]
  T1 --> T2[02 Baseline agent]
  T2 --> T3[03 Router and cache]
  T3 --> T4[04 Production queue]
```

| Tab | Notebook | What happens when you use it |
|-----|----------|------------------------------|
| 📖 **00. UI Guide** | — | Renders this guide in the dashboard — documentation only |
| 🚀 **01. Readiness Check** | `00_initialization.ipynb` | Probes live services — no questions are answered |
| 🤖 **02. Complex Agent** | `01_agent.ipynb` | Every question embeds, searches Redis, and invokes the full agent |
| ⚖️ **03. Router & Cache** | `02_router_cache.ipynb` | Questions are classified, cached, or deflected before spend accrues |
| 🏭 **04. Production Queue** | `03_async_work_queue.ipynb` | Questions are queued; workers run the Tab 3 pipeline off-thread |

---

## 📖 00. UI Guide

This tab renders **`docs/embeded_guide.md`** inside Streamlit — tab walkthrough, screenshots, and configuration reference. Nothing calls Redis or the models from here. Edit **`docs/embeded_guide.md`** for in-dashboard content; this file adds getting started, deploy, and troubleshooting.

---

## 🚀 01. Readiness Check

Before you spend tokens, this tab **asks the cluster whether it can actually run the demo**. Click **Run Preflight Checks** and the UI runs four probes in sequence:

1. **Redis** — opens a connection, sends `PING`, and reads the server version. This confirms vector search, router, cache, and queue features have a broker to talk to.
2. **Simple model** — sends a one-token chat completion to your MaaS gateway. This validates credentials, routing, and that the cheaper model is reachable.
3. **Complex model** — same probe against the reasoning model Tab 2 and Tab 3 fall back to on cache miss.
4. **RAK worker** — inspects the Redis Streams consumer group. It does not enqueue work; it only checks whether a worker process is subscribed and listening.

If everything responds, you get a green banner and latency numbers on each card. If the worker probe returns **idle**, Redis and the models may still be fine — Tab 4 will accept enqueue requests but nothing will drain the queue until you start a worker (`insuranceWorker` on OpenShift, or `rak worker` locally).

![Infrastructure verification demo](images/infra-verification.png)

---

## 🤖 02. Complex Agent

This tab **always takes the expensive path** so you have a baseline to compare against Tab 3.

When you submit a question, the UI:

1. Sends your text to the LangGraph ReAct agent with a fixed session id (`ui-tab2-agent`).
2. Lets the agent decide whether to call Redis Vector Search tools (FAQ lookup, policy lookup).
3. Streams the final answer into the chat column.
4. Records token usage and estimated cost in **Under the Hood**.

![Base Line Model Cost and Behavior](./images/baseline-expirience.png)

Nothing is classified and nothing is cached — every submission pays the full complex-model price. That is intentional. After you try Tab 3, come back here mentally: *"This is what every request would cost without routing."*

The metrics panel updates only after a run completes. If tools fired, you will see which vector searches ran; that context is part of why the complex path costs more than a single chat completion.

![Base Line Model Cost and Behavior](./images/baseline-expirience.png)

---

## ⚖️ 03. Router & Cache

This tab **changes where your question goes** before any LLM work happens.

![Const Analysis](images/cost-saving-analysis.png)

### What happens on each submit

When you click a preset or **Send through pipeline**, the UI runs the same pipeline as `demo/shared/insurance_pipeline.py`:

```mermaid
flowchart TD
  Q[Your question] --> E[Embed query]
  E --> R{Semantic router}
  R -->|blocked| X[Reject — no LLM]
  R -->|simple| S[Cheaper model only]
  R -->|complex| C{Semantic cache lookup}
  C -->|hit| H[Return stored answer]
  C -->|miss| A[Full complex agent]
  A --> AC[Auto-cache answer if enabled]
```

1. **Embed** — the question is vectorized (same embedding model as the notebooks).
2. **Route** — Redis vector search classifies intent as `simple`, `complex`, or `blocked` in milliseconds, with no LLM tokens spent on classification.
3. **Cache** (complex only) — Redis searches for a semantically similar approved answer. A hit skips the agent entirely.
4. **Agent** (cache miss only) — the full LangGraph path from Tab 2 runs, then the answer can be stored for future hits.

The pipeline diagram highlights which stage handled your last request. Outcome banners tell you the result in plain language: blocked, simple deflection, cache hit, or cache miss.

### Using the presets deliberately

The four preset buttons are a guided tour — run them in order to *see* the pipeline change behavior:

- **Simple** — watch the router send a FAQ-style payment question to the cheap model. The agent stage never activates.
- **Blocked** — submit an injection-style prompt and confirm zero LLM spend.
- **Complex (cache miss)** — forces a cache miss so you see the agent path and a fresh answer land in Redis (when `INSURANCE_AUTO_CACHE=true`).
- **Complex (cache hit)** — ask a near-duplicate of the miss preset and watch spend drop to near zero as the cache returns the stored answer.

After each run, the session cost panel **recalculates ROI**: it compares what you actually spent to a counterfactual where every question went through the Tab 2 agent with full context. **Total saved**, **Deflected**, and the per-path counters accumulate across the session until you **Reset cost counters** (that reset only clears UI totals — it does not wipe Redis cache entries).

Thumbs up / down on the last answer let you explicitly approve or reject re-storing in the semantic cache. With auto-cache on, approval is mostly confirmatory; thumbs down skips an extra write if the answer was not helpful.

---

## 🏭 04. Production Queue

Tab 3 runs inference **inside the Streamlit process** — your browser waits while the model thinks. Tab 4 **decouples submission from execution**: the UI only enqueues work; RAK workers do the same router → cache → agent pipeline asynchronously.

When you click **Simulate Production Traffic**:

1. The UI picks N preset questions (slider controls batch size).
2. Each question is published to the `insurance` Redis Stream via Docket (`run_agent` handler).
3. The page starts polling every ~0.6s — you see queue depth drop and task rows move `PENDING` → `PROCESSING` → `COMPLETED`.
4. Worker log lines append as tasks report progress.
5. When every task reaches a terminal status, polling stops and a batch summary appears.

From the UI's perspective, nothing blocks on model latency. From the worker's perspective, each task is identical to a Tab 3 pipeline run — same router, same cache, same agent — just executed in a separate pod/process that can scale horizontally.

If **Active workers** stays at zero, tasks pile up in the stream until you deploy `insuranceWorker` or run `rak worker --name insurance --tasks insurance_worker:tasks --concurrency 4` locally. Tab 1's worker probe catches this before you waste time wondering why nothing moves.

![Simulate Production Traffic](images/production-worker-queue.png)

---

## Configuration that changes behavior

These environment variables alter *what the tabs do*, not just labels on screen:

| Variable | What it changes |
|----------|-----------------|
| `INSURANCE_AUTO_CACHE` | When `true`, Tab 3 stores fresh complex answers automatically after cache miss. |
| `INSURANCE_PLAIN_COMPLEX` | When `true`, complex path uses a single MaaS completion (no tool-calling) — needed for gateways without auto tool choice. |
| `ROI_*` pricing | Tab 3 dollar estimates and savings percentages. |
| `REDIS_URL` | Shared by router, cache, agent memory, and Tab 4 queue — one broker, multiple roles. |

Full install and secret wiring: [README.md](../README.md), [deploy/README.md](../deploy/README.md).
