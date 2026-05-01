# Deploy — OpenShift notebook

This folder contains a single **Helm chart** (`deploy/helm`, release name `redis-notebook`) that provisions a Jupyter workbench with a persistent workspace and a **post-install Job** that clones this repository and copies the **`demo/`** tree into the notebook’s work directory so you can run the quickstart notebooks.

The chart supports two **notebook delivery modes** (controlled by `notebook.kind` in `deploy/helm/values.yaml`):

| Mode | When to use |
|------|----------------|
| **`Deployment`** (default) | Plain `Deployment` + `Service` + `Route` using the public **Open Data Hub minimal workbench** image (`quay.io/opendatahub/odh-workbench-jupyter-minimal-cpu-py312-ubi9`). Works on any OpenShift cluster — no RHOAI / ODH notebook-controller required. No injected OAuth proxy; configure `notebook.auth.token` if you need browser auth. |
| **`Notebook`** | Kubeflow `kubeflow.org/v1` **`Notebook`** CR. Requires **Red Hat OpenShift AI** (or upstream **Open Data Hub** notebook-controller) installed on the cluster — the chart fails fast with a friendly error if the CRD is missing. Gives you the dashboard workbench experience and OAuth-proxy auth via `notebooks.opendatahub.io/inject-auth`. |

The same chart installs **Redis** for the notebooks using one of four modes (see **`redis.useOtContainerKitOperator`**, **`redis.useRedisEnterpriseOperator`**, and **`redis.builtin.enabled`** in `deploy/helm/values.yaml`):

| Mode | When to use |
|------|----------------|
| **Redis Enterprise Operator (REC + REDB)** (default) | `redis.useRedisEnterpriseOperator: true`. By default the chart also applies OLM **OperatorGroup** + **Subscription** for **redis-enterprise-operator-cert** (`certified-operators`) into the **release namespace** (OwnNamespace). It then creates `RedisEnterpriseCluster` + `RedisEnterpriseDatabase` and wires the notebook to the auto-generated DB password Secret. Set **`redis.enterprise.olm.enabled: false`** to skip OLM and install the operator from OperatorHub yourself first. |
| **Builtin Redis Stack** | Set `redis.useRedisEnterpriseOperator: false` and `redis.builtin.enabled: true`. In-chart `Deployment` + `Service` using `docker.io/redis/redis-stack-server` — no cluster-wide operator, no admin install. Supports **redisvl** / semantic cache (`02_router_cache.ipynb`). |
| **OT-CONTAINER-KIT operator + Redis CR** | Set `redis.useOtContainerKitOperator: true` (and `redis.useRedisEnterpriseOperator: false`), run `helm dependency update`, install once (cluster-scoped RBAC). Use if your platform standardizes on this operator. |
| **External Redis** | All three flags off (`redis.useOtContainerKitOperator`, `redis.useRedisEnterpriseOperator`, `redis.builtin.enabled`), set **`secrets.redis.url`** to your broker. |

## Prerequisites

- OpenShift cluster with **`oc`** and **`helm`** configured. The default `Deployment` mode runs on any vanilla OpenShift cluster; **only the `Notebook` mode** additionally requires **Red Hat OpenShift AI** (or upstream **Open Data Hub** notebook-controller). Quick check:
  ```bash
  oc get crd notebooks.kubeflow.org   # required only for notebook.kind=Notebook
  ```
- A **workbench image** the cluster can pull. Default is `quay.io/opendatahub/odh-workbench-jupyter-minimal-cpu-py312-ubi9:latest` (publicly pullable, OpenShift-SCC-friendly). For `Notebook` mode on RHOAI, override to the in-cluster image stream, e.g. `image-registry.openshift-image-registry.svc:5000/redhat-ods-applications/tensorflow:2025.2`.
- **Helm 3** with access to `https://ot-container-kit.github.io/helm-charts/` **only if** you enable **`redis.useOtContainerKitOperator`** (then run `make -f deploy/helm/Makefile deps`). Builtin Redis does not require that registry.
- **Cluster administrator** privileges the first time you install the bundled **redis-operator** subchart (cluster-scoped RBAC). If an OT redis-operator is already installed, keep **`redis.useOtContainerKitOperator: false`** (builtin Redis) or set it **`true`** and coordinate with your admin so you do not duplicate the operator.
- **Redis Enterprise Operator** — when **`redis.useRedisEnterpriseOperator`** is true (default), the chart installs OLM resources (**`redis.enterprise.olm`**, on by default) so **`redis-enterprise-operator-cert`** is subscribed in the release namespace. You need catalog **`certified-operators`** in **`openshift-marketplace`** and permission to create **OperatorGroup** / **Subscription**. If the namespace already has an **OperatorGroup**, set **`redis.enterprise.olm.createOperatorGroup: false`**. To install the operator only via the console, set **`redis.enterprise.olm.enabled: false`**. The chart fails fast if the `app.redislabs.com` CRDs are missing. Quick check:
  ```bash
  oc get crd redisenterpriseclusters.app.redislabs.com redisenterprisedatabases.app.redislabs.com
  ```
- **`deploy/helm/values-secret.yaml`** — not committed (see `deploy/helm/.gitignore`). **`make deploy`** refuses to run until this file exists; copy from **`values-secret.example.yaml`** and set at least **`secrets.model.apiKey`**.
- **PyYAML** — `make deploy` runs **`validate-secrets`**, which merges `values.yaml` + `values-secret.yaml` in Python and rejects **null** or **empty** required fields. Install if needed: **`python3 -m pip install pyyaml`**.

## Layout

| Path | Purpose |
|------|---------|
| `helm/Chart.yaml` | Chart metadata (`redis-notebook`) and optional **Helm dependencies** (`redis-operator`, `redis` as `redisData`) when `redis.useOtContainerKitOperator` is true. |
| `helm/Chart.lock` / `helm/charts/*.tgz` | Locked dependency versions (run `make -f deploy/helm/Makefile deps` after changing `Chart.yaml` or enabling the operator path). |
| `helm/values.yaml` | Notebook, git clone, Redis mode (builtin vs operator vs external); non-secret defaults. |
| `helm/values-secret.example.yaml` | Template for **`values-secret.yaml`** (copy locally; gitignored). Holds `secrets.model.*` and optional `secrets.redis.url`. |
| `helm/templates/` | `_helpers.tpl`, `NOTES.txt`, and subfolders: **`notebook/`** (Workbench, workspace PVC, git-clone Job), **`redis-builtin/`** (Stack Deployment/Service/PVC/ConfigMap), **`redis-enterprise/`** (OLM OperatorGroup/Subscription when enabled, REC, REDB), **`rbac/`** (ServiceAccount, RoleBinding). |
| `helm/Makefile` | Shortcuts for `deps`, `lint`, `template`, `check-secrets`, `validate-secrets`, `deploy`, `undeploy`, `logs-clone`. |
| `helm/scripts/validate_secrets.py` | Merges values like Helm and fails on empty/null **`secrets.model.*`** (and **`secrets.redis.url`** when using external Redis only). |

## Quick deploy (Make)

From the repository root:

```bash
cp deploy/helm/values-secret.example.yaml deploy/helm/values-secret.yaml
# Edit deploy/helm/values-secret.yaml — set secrets.model.apiKey (and anything else you need)

make -f deploy/helm/Makefile help
make -f deploy/helm/Makefile deploy
```

Defaults: **namespace** and **release name** `redis-notebook`. Override as needed:

```bash
make -f deploy/helm/Makefile deploy NAMESPACE=my-project RELEASE_NAME=my-release
```

Useful targets:

- **`deps`** — `helm dependency update` (downloads / refreshes `redis-operator` and `redis` charts into `helm/charts/`). Needed before deploy when using the operator path.
- **`lint`** — `helm lint` on the chart.
- **`template`** — render manifests without applying.
- **`check-secrets`** — fails fast if **`values-secret.yaml`** is missing.
- **`validate-secrets`** — requires **`check-secrets`**, then ensures merged values have no null/empty required **`secrets.*`** fields (uses PyYAML).
- **`deploy`** — runs **`validate-secrets`**, **`deps`**, creates the namespace, then `helm upgrade --install` with **`values.yaml`** and **`values-secret.yaml`**.
- **`logs-clone`** — logs from the git-clone Job pods.
- **`undeploy`** — `helm uninstall` (namespace is not deleted; the PVC may remain because of `helm.sh/resource-policy: keep` on the PVC).

## Quick deploy (Helm only)

**Redis Enterprise Operator (REC + REDB) — default.** The chart applies **OperatorGroup** + **Subscription** for **redis-enterprise-operator-cert** unless you set **`redis.enterprise.olm.enabled: false`**.

```bash
cp ./deploy/helm/values-secret.example.yaml ./deploy/helm/values-secret.yaml
# Edit values-secret.yaml (at least secrets.model.apiKey)

oc new-project redis-notebook           # or choose your own namespace
helm upgrade --install redis-notebook ./deploy/helm \
  --namespace redis-notebook \
  --values ./deploy/helm/values.yaml \
  --values ./deploy/helm/values-secret.yaml \
  --wait --timeout 15m
```

The chart will refuse to render if the `app.redislabs.com` CRDs are not registered on the cluster. After install, wait for the **CSV** to reach **Succeeded** (`oc get csv -n redis-notebook -w`) before `rec` / `redb` reconcile. Tune cluster size / database resources via `redis.enterprise.cluster.*` and `redis.enterprise.database.*` in `values.yaml`.

**Builtin Redis Stack** — no operator install required, useful for laptop / vanilla OpenShift demos:

```bash
helm upgrade --install redis-notebook ./deploy/helm \
  --namespace redis-notebook \
  --values ./deploy/helm/values.yaml \
  --values ./deploy/helm/values-secret.yaml \
  --set redis.useRedisEnterpriseOperator=false \
  --set redis.builtin.enabled=true \
  --wait --timeout 10m
```

**OT operator + Redis CR**:

```bash
helm dependency update ./deploy/helm
helm upgrade --install redis-notebook ./deploy/helm \
  --namespace redis-notebook \
  --values ./deploy/helm/values.yaml \
  --values ./deploy/helm/values-secret.yaml \
  --set redis.useRedisEnterpriseOperator=false \
  --set redis.useOtContainerKitOperator=true \
  --set redis.builtin.enabled=false \
  --wait --timeout 10m
```

If **redis-operator** is already on the cluster, avoid duplicate cluster RBAC: keep **`redis.useOtContainerKitOperator: false`** and use **builtin** Redis, or install only the `redisData` instance from a shared operator (advanced — not split in this chart).

## What the chart creates

**When `redis.useOtContainerKitOperator` is true**, the **[OT-CONTAINER-KIT redis-operator](https://github.com/OT-CONTAINER-KIT/redis-operator)** subchart installs the operator Deployment plus **cluster-scoped** RBAC (unless already satisfied), and the **`redisData`** subchart creates a **`Redis`** custom resource for a **standalone** Redis 7 instance.

**When `redis.useRedisEnterpriseOperator` is true**, the chart optionally (**`redis.enterprise.olm`**, default on) creates an **OperatorGroup** and **Subscription** so OLM installs **redis-enterprise-operator-cert** in the release namespace, then creates a **`RedisEnterpriseCluster`** (`app.redislabs.com/v1`, default 3 nodes with persistence) and a **`RedisEnterpriseDatabase`** (`app.redislabs.com/v1alpha1`, single shard with replication by default). The operator reconciles these into a Redis Enterprise StatefulSet, an internal admin service, and a per-database service named after `redis.enterprise.database.name` (default `redb`). The operator also creates a Secret named **`redb-<database.name>`** holding the auto-generated `password`, `port`, and `service_names`; the notebook deployment mounts `password` and `port` via `secretKeyRef` and composes `REDIS_URL` with Kubernetes `$(VAR)` interpolation.

**When `redis.useOtContainerKitOperator` is false and `redis.builtin.enabled` is true**, the chart creates a **Deployment** and **ClusterIP Service** for **Redis Stack** (`redis.builtin.image`), optional **PVC** for persistence, and an optional **ConfigMap** (`redis.connectionConfigMap`) with `REDIS_URL` / `REDIS_HOST` / `REDIS_PORT` for debugging or extra consumers.

**When all three flags are off**, no in-cluster Redis is created; the notebook **`REDIS_URL`** comes from **`secrets.redis.url`**.

Other resources:

1. **ServiceAccount** and **RoleBinding** to the cluster **`edit`** role so the workbench workload can use the namespace as expected.
2. **PersistentVolumeClaim** — read-write-once workspace for `/opt/app-root/src` (annotation keeps the PVC across uninstall if you rely on that policy).
3. **Notebook workload** — depends on `notebook.kind`:
   - `Deployment` (default): a plain `Deployment` + `ClusterIP` `Service` + OpenShift `Route` (edge TLS) using the configured image, probes, and a `/dev/shm` emptyDir.
   - `Notebook`: a `kubeflow.org/v1` `Notebook` CR; the RHOAI / ODH notebook-controller reconciles it into a `StatefulSet` + `Service` + `Route` with an injected OAuth proxy.
4. **Job** (post-install / post-upgrade hook) — waits for the PVC, clones `notebook.gitSync.repo` (optional branch), copies **`demo/`** into the workspace root, then exits. Notebooks appear under **`demo/notebooks`** inside the workspace (i.e. `/opt/app-root/src/demo/notebooks` in the container).

The notebook **`REDIS_URL`** environment variable is set from **`redis-notebook.redisUrl`** in templates: FQDN in-cluster DNS for operator or builtin Redis, or **`secrets.redis.url`** for external-only.

Disable the clone Job by setting `notebook.gitSync.enabled: false` in a custom values file.

## Demo notebooks — runtime expectations

The `demo/notebooks` flow (and `demo/shared/insurance_bot.py`) expect:

| Item | Notes |
|------|--------|
| **OpenAI-compatible LLM** | `MODEL_API_KEY` (required), `MODEL_ENDPOINT` (default `https://api.openai.com`), `SIMPLE_MODEL_NAME` / `COMPLEX_MODEL_NAME` with defaults. The chart injects these from `values.yaml` layered with **`values-secret.yaml`** (`secrets.model.*`). |
| **Redis URL** | `REDIS_URL` — builtin or operator in-cluster URL, or `secrets.redis.url` when external. **Builtin** image is Redis Stack (redisvl-friendly). |
| **`.env` in repo root** | Notebooks call `load_dotenv(REPO_ROOT / ".env")` with `REPO_ROOT` resolved from `demo/notebooks`; chart env vars still apply for missing keys. |
| **`TOKENIZERS_PARALLELISM`** | Set to `false` inside `02_router_cache.ipynb` to silence Hugging Face tokenizer fork warnings. |
| **Python dependencies** | Install from `demo/scripts/requirements.txt` in the workbench (or bake into a custom image). RHOAI / Red Hat curated PyPI may omit **`redisvl`** — use `--extra-index-url https://pypi.org/simple` or rely on **`notebook.pipExtraIndexUrl`** (default) so the chart sets **`PIP_EXTRA_INDEX_URL`** on the pod. |

**Plain OSS Redis:** To use `docker.io/library/redis` (e.g. `7.2-alpine`) instead of Stack, set `redis.builtin.image.repository` / `redis.builtin.image.tag` in overrides. Notebook **02** (redisvl) needs **RediSearch** / Stack capabilities.

## Important configuration (`values.yaml`)

| Area | Keys | Notes |
|------|------|--------|
| OpenShift | `global.openshift` | Currently informational; templates render on any cluster (`Route` is gated on the OpenShift Route CRD via `Capabilities.APIVersions`). |
| Notebook mode | `notebook.kind` | `Deployment` (default, no RHOAI required) or `Notebook` (Kubeflow CR — needs RHOAI / ODH). |
| Redis mode | `redis.useOtContainerKitOperator`, `redis.useRedisEnterpriseOperator`, `redis.builtin.enabled` | OT operator+CR vs Redis Enterprise REC+REDB vs in-chart Deployment vs external (`secrets.redis.url`). At most one operator flag should be true. |
| Builtin Redis | `redis.builtin.image`, `redis.builtin.persistence`, `redis.builtin.resources` | Redis Stack defaults; optional PVC. |
| Redis Enterprise | `redis.enterprise.cluster.*`, `redis.enterprise.database.*`, `redis.enterprise.olm.{enabled,createOperatorGroup,operatorGroupName,skipCapabilityCheck,subscription.*}` | Only when `redis.useRedisEnterpriseOperator: true`. **OLM** (`redis.enterprise.olm`, default on) installs **redis-enterprise-operator-cert** via **Subscription** + **OperatorGroup**. Defaults to a 3-node cluster with persistence and a single-shard replicated database `redb`. The notebook reads `password` / `port` from the operator-generated `redb-<database.name>` Secret unless you override `passwordSecretName`. |
| ConfigMap | `redis.connectionConfigMap.enabled`, `redis.connectionConfigMap.name` | Exposes `REDIS_URL` for `oc` inspection; notebook env is set independently. Suppressed in Redis Enterprise mode (the URL contains a `$(VAR)` placeholder that is only resolved inside the notebook pod). |
| Identity | `notebook.username` | Passed to `opendatahub.io/username` for dashboard integration in `Notebook` mode. |
| Image | `notebook.image.repository`, `notebook.image.tag` | Default is the public ODH minimal workbench image. Must match an image your cluster can resolve. |
| Pip / PyPI | `notebook.pipExtraIndexUrl` | Default `https://pypi.org/simple` sets **`PIP_EXTRA_INDEX_URL`** so `pip install` finds **`redisvl`** when the workbench uses a curated index (e.g. RHOAI). Set to `""` for air-gapped clusters. |
| Auth | `notebook.auth.token` | `Deployment` mode only. Empty = no auth (public Route); set a token to require it. Ignored when `kind=Notebook` (RHOAI handles auth). |
| Route | `notebook.route.enabled`, `notebook.route.host` | `Deployment` mode only. `enabled: false` skips the Route (port-forward instead). Empty `host` → cluster wildcard domain. |
| Resources | `notebook.resources` | CPU and memory requests/limits for the notebook container. |
| Storage | `notebook.storage.size`, `notebook.storage.storageClassName` | PVC size; leave storage class empty to use the default class. |
| Git | `notebook.gitSync.repo`, `notebook.gitSync.branch` | Point at your fork or branch if needed. |
| RBAC | `serviceAccount.create`, `rbac.create` | Set to `false` only if you supply your own SA and bindings. |
| OT operator path | `redisData.*`, `redis-operator.redisOperator.watchNamespace` | Only when `redis.useOtContainerKitOperator` is true. |
| External Redis | `redis.builtin.enabled: false`, `secrets.redis.url` | No chart-managed Redis. Both operator flags must also be `false`. |

Example override for a fork:

```bash
helm upgrade --install redis-notebook ./deploy/helm \
  --namespace redis-notebook \
  --values ./deploy/helm/values.yaml \
  --values ./deploy/helm/values-secret.yaml \
  --set notebook.gitSync.repo=https://github.com/<org>/Reducing-costs-of-AI-with-Redis-Labs.git \
  --set notebook.gitSync.branch=main
```

## After install

- **`Deployment` mode (default)**: `helm status <release> -n <namespace>` prints the Route URL (`NOTES.txt`). The notebook is reachable at `https://<route-host>/lab` once the pod is `Ready`. With `notebook.auth.token` empty, the Route is unauthenticated; set the token in `values.yaml` (or restrict the Route via NetworkPolicy) before sharing the URL.
- **`Notebook` mode**: open **OpenShift AI → Data Science Projects**, select the namespace, and open the workbench when it is ready. The OAuth proxy injected by the notebook-controller handles auth.
- **Redis Enterprise mode**: with **`redis.enterprise.olm.enabled`** (default **true**), the chart creates the **Subscription** in the release namespace; wait until **`oc get csv -n <namespace>`** shows **Succeeded** so `rec` / `redb` reconcile and the **`redb-<database.name>`** Secret appears. If OLM is disabled, install the operator from OperatorHub first. If `rec`/`redb` were created before the CSV succeeded, delete those CRs or reinstall after the operator is healthy. The notebook Deployment stays in **Init** until the Secret exists. Inspect credentials with `oc get secret redb-<database.name> -n <namespace> -o yaml`.
- If the clone Job fails (network, private repo, or volume contention), check **`make -f deploy/helm/Makefile logs-clone`** or inspect the Job pods in the namespace. With **ReadWriteOnce** storage, only one pod can mount the PVC at a time; if the notebook pod already holds the claim, the clone Job may not schedule until that pod releases the volume—stop the notebook workload temporarily if you need to re-run the clone, or adjust storage / workflow for your environment.

## Remove the release

```bash
make -f deploy/helm/Makefile undeploy
# or
helm uninstall redis-notebook --namespace redis-notebook
```

Delete the namespace separately if you no longer need it; delete any retained PVCs if you want a full cleanup of stored workspace data.
