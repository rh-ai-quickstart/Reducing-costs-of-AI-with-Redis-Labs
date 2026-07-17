# Run Redis locally

The `demo/` folder contains everything needed to exercise the router + cache + agent pattern against a local Redis instance and an OpenAI-compatible API.

## Requirements

- Python 3.11+ (3.12 is fine)
- **Redis** reachable at `REDIS_URL` (default `redis://localhost:6379`). Use **Redis Stack** if you run **`02_router_cache.ipynb`** (semantic router / cache need search modules). **`01_agent.ipynb`** LangGraph multi-turn memory needs **`langgraph-checkpoint-redis`** (see `demo/scripts/requirements.txt`).
- An API key for your LLM provider (OpenAI by default; override **`MODEL_ENDPOINT`** for OpenShift AI / vLLM / Azure OpenAI–compatible hosts)

**1. Install dependencies**

```bash
cd Reducing-costs-of-AI-with-Redis-Labs
python -m venv .venv && source .venv/bin/activate
pip install -r demo/scripts/requirements.txt --extra-index-url https://pypi.org/simple
```

**2. Configure the environment**

Create a `.env` file at the repository root:

```dotenv
MODEL_API_KEY=sk-...
MODEL_ENDPOINT=https://api.openai.com
SIMPLE_MODEL_NAME=gpt-4.1
COMPLEX_MODEL_NAME=gpt-5
REDIS_URL=redis://localhost:6379
```

**3. Run the notebooks**

```bash
jupyter lab demo/notebooks
```

Run from the **`demo/notebooks`** directory (or ensure that is the notebook working directory) so paths to `data/` and repo-root `.env` resolve as in the notebooks.

| Notebook | What it shows |
|---|---|
| `00_initialization.ipynb` | Optional smoke test: env vars, Redis `PING`, and model endpoint checks. |
| `01_agent.ipynb` | Step-by-step LangGraph ReAct agent (FAQ, policy tools, Redis-backed checkpointer). |
| `02_router_cache.ipynb` | Imports `demo/shared/insurance_bot.py`: semantic router, thumbs-up–only semantic cache, agent with Redis memory. |
| `03_async_work_queue.ipynb` | Uses [redis-agent-kit](https://pypi.org/project/redis-agent-kit/) for an async Redis-backed work queue across workers. |

## Uninstall local deployment

Local setup has no cluster release. Deactivate the virtualenv and remove it if you no longer need it:

```bash
deactivate
rm -rf .venv
```