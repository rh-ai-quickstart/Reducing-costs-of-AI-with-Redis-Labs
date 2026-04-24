# Deploy — OpenShift AI notebook

This folder contains a small **Helm chart** that provisions an **OpenShift AI (RHOAI) Kubeflow `Notebook`** with a persistent workspace and a **post-install Job** that clones this repository and copies the **`demo/`** tree into the notebook’s work directory so you can run the quickstart notebooks from the dashboard.

## Prerequisites

- OpenShift cluster with **OpenShift AI** (or equivalent **OpenShift Data Science** / **Kubeflow Notebook** controller) installed.
- **`oc`** and **`helm`** configured for the cluster.
- A **workbench image** available in the cluster (default in `values.yaml` pulls from the internal OpenShift registry path `redhat-ods-applications/tensorflow`, which is typical on RHOAI).
- **Helm 3** with access to `https://ot-container-kit.github.io/helm-charts/` (for `helm dependency update`), unless you vendor the `charts/*.tgz` bundles already in the repo.
- **Cluster administrator** privileges the first time you install the bundled **redis-operator** subchart (it creates cluster-scoped RBAC). If an OT redis-operator is already installed, set **`redis.operator.enabled`** to **`false`** so this release only creates the Redis instance and the notebook.

## Layout

| Path | Purpose |
|------|---------|
| `helm/Chart.yaml` | Chart metadata (`redis-notebook`) and **Helm dependencies** (`redis-operator`, `redis` as `redisData`). |
| `helm/Chart.lock` / `helm/charts/*.tgz` | Locked dependency versions (run `make -f deploy/helm/Makefile deps` after changing `Chart.yaml`). |
| `helm/values.yaml` | Notebook, secrets, git clone, and Redis / operator settings. |
| `helm/templates/` | Kubernetes / OpenShift manifests (Notebook, PVC, RBAC, clone Job). |
| `helm/Makefile` | Shortcuts for `deps`, `lint`, `template`, `deploy`, `undeploy`, `logs-clone`. |

## Quick deploy (Make)

From the repository root:

```bash
make -f deploy/helm/Makefile help
make -f deploy/helm/Makefile deploy
```

Defaults: **namespace** and **release name** `redis-notebook`. Override as needed:

```bash
make -f deploy/helm/Makefile deploy NAMESPACE=my-project RELEASE_NAME=my-release
```

Useful targets:

- **`deps`** — `helm dependency update` (downloads / refreshes `redis-operator` and `redis` charts into `helm/charts/`).
- **`lint`** — `helm lint` on the chart.
- **`template`** — render manifests without applying.
- **`deploy`** — runs **`deps`**, creates the namespace, then `helm upgrade --install --wait`.
- **`logs-clone`** — logs from the git-clone Job pods.
- **`undeploy`** — `helm uninstall` (namespace is not deleted; the PVC may remain because of `helm.sh/resource-policy: keep` on the PVC).

## Quick deploy (Helm only)

```bash
helm dependency update ./deploy/helm   # first time, or after editing Chart dependencies
oc new-project redis-notebook           # or choose your own namespace
helm upgrade --install redis-notebook ./deploy/helm \
  --namespace redis-notebook \
  --values ./deploy/helm/values.yaml \
  --wait --timeout 10m
```

If **redis-operator** is already on the cluster, avoid duplicate cluster RBAC:

```bash
helm upgrade --install redis-notebook ./deploy/helm \
  --namespace redis-notebook \
  --values ./deploy/helm/values.yaml \
  --set redis.operator.enabled=false \
  --wait --timeout 10m
```

## What the chart creates

When **`redis.operator.enabled`** is true (default), the **[OT-CONTAINER-KIT redis-operator](https://github.com/OT-CONTAINER-KIT/redis-operator)** subchart installs the operator Deployment plus **cluster-scoped** RBAC so it can reconcile `Redis` custom resources.

When **`redis.enabled`** is true (default), the **`redisData`** subchart creates a **`Redis`** custom resource (`redis.redis.opstreelabs.in/v1beta2`) for a **standalone** Redis 7 instance (see `redisData` in `values.yaml` for storage and naming). The operator materializes StatefulSet / Service resources in the release namespace.

Other resources:

1. **ServiceAccount** and **RoleBinding** to the cluster **`edit`** role (pre-install hooks) so the workbench workload can use the namespace as expected.
2. **PersistentVolumeClaim** — read-write-once workspace for `/opt/app-root/src` (annotation keeps the PVC across uninstall if you rely on that policy).
3. **`Notebook`** (`kubeflow.org/v1`) — Jupyter-compatible workbench using the configured image, probes, and optional `/dev/shm` emptyDir.
4. **Job** (post-install / post-upgrade hook) — waits for the PVC, clones `notebook.gitSync.repo` (optional branch), copies **`demo/`** into the workspace root, then exits. Notebooks appear under **`demo/notebooks`** inside the workspace (i.e. `/opt/app-root/src/demo/notebooks` in the container).

The notebook **`REDIS_URL`** environment variable is set automatically to in-cluster DNS when **`redis.enabled`** is true: `redis://<redis-name>.<namespace>.svc.<clusterDomain>:6379`, where `<redis-name>` is `redisData.redisStandalone.name` or, if empty, the **Helm release name**. Set **`redis.enabled`** to **`false`** to point the notebook at an external broker using **`secrets.redis.url`** instead.

Disable the clone Job by setting `notebook.gitSync.enabled: false` in a custom values file.

## Demo notebooks — runtime expectations

The `demo/notebooks` flow (and `demo/shared/insurance_bot.py`) expect:

| Item | Notes |
|------|--------|
| **OpenAI-compatible LLM** | `MODEL_API_KEY` (required), `MODEL_ENDPOINT` (default `https://api.openai.com`), `SIMPLE_MODEL_NAME` / `COMPLEX_MODEL_NAME` with defaults. The chart injects these from `values.yaml` / `values-secrets.yaml`. |
| **Redis URL** | `REDIS_URL` — wired from in-cluster Redis (above) or `secrets.redis.url` when `redis.enabled` is false. Uses plain **Redis 7** TCP (`redis://…`). |
| **`.env` in repo root** | Notebooks call `load_dotenv(REPO_ROOT / ".env")` with `REPO_ROOT` resolved from `demo/notebooks`; chart env vars still apply for missing keys. |
| **`TOKENIZERS_PARALLELISM`** | Set to `false` inside `02_router_cache.ipynb` to silence Hugging Face tokenizer fork warnings. |
| **Python dependencies** | Install packages from `demo/scripts/requirements.txt` in the workbench (or bake them into a custom image) before running cells. |

**Redis Stack / modules:** LangGraph’s `RedisSaver` and basic Redis clients work against the bundled **open source Redis** image. If you later add **vector / RediSearch** features (for example RedisVL semantic indexes), you must run a **Redis Stack**–capable image or **Redis Enterprise** and adjust `redisData.redisStandalone.image` / operator configuration accordingly—the default chart does not enable Redis Stack modules.

## Important configuration (`values.yaml`)

| Area | Keys | Notes |
|------|------|--------|
| OpenShift | `global.openshift` | Must be `true` for the `Notebook` and PVC templates to render. |
| Identity | `notebook.username` | Passed to `opendatahub.io/username` for dashboard integration. |
| Image | `notebook.image.repository`, `notebook.image.tag` | Must match an image stream or pull spec your cluster can resolve. |
| Resources | `notebook.resources` | CPU and memory requests/limits for the notebook container. |
| Storage | `notebook.storage.size`, `notebook.storage.storageClassName` | PVC size; leave storage class empty to use the default class. |
| Git | `notebook.gitSync.repo`, `notebook.gitSync.branch` | Point at your fork or branch if needed. |
| RBAC | `serviceAccount.create`, `rbac.create` | Set to `false` only if you supply your own SA and bindings. |
| Redis | `redis.enabled`, `redis.operator.enabled` | Instance vs operator toggles; see above. |
| Redis sizing | `redisData.storageSpec`, `redisData.redisStandalone` | PVC size and Redis CR overrides (image, resources, name). |
| Operator scope | `redis-operator.redisOperator.watchNamespace` | Empty string watches all namespaces; set to your project name to limit reconciliation if your operator chart supports it. |
| External Redis | `redis.enabled: false`, `secrets.redis.url` | Use a managed Redis URL instead of the subchart. |

Example override for a fork:

```bash
helm upgrade --install redis-notebook ./deploy/helm \
  --namespace redis-notebook \
  --set notebook.gitSync.repo=https://github.com/<org>/Reducing-costs-of-AI-with-Redis-Labs.git \
  --set notebook.gitSync.branch=main
```

## After install

- Open **OpenShift AI → Data Science Projects** (or your deployment’s workbench UI), select the namespace, and open the **Notebook** workload when it is ready.
- If the clone Job fails (network, private repo, or volume contention), check **`make -f deploy/helm/Makefile logs-clone`** or inspect the Job pods in the namespace. With **ReadWriteOnce** storage, only one pod can mount the PVC at a time; if the notebook pod already holds the claim, the clone Job may not schedule until that pod releases the volume—stop the notebook workload temporarily if you need to re-run the clone, or adjust storage / workflow for your environment.

## Remove the release

```bash
make -f deploy/helm/Makefile undeploy
# or
helm uninstall redis-notebook --namespace redis-notebook
```

Delete the namespace separately if you no longer need it; delete any retained PVCs if you want a full cleanup of stored workspace data.
