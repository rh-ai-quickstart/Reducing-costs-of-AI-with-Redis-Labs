# Deploy — OpenShift notebook

This folder contains a single **Helm chart** (`deploy/helm`, release name `redis-notebook`) that provisions a Jupyter workbench with a persistent workspace and a **post-install Job** that clones this repository and copies the **`demo/`** tree into the notebook’s work directory so you can run the quickstart notebooks.

The chart supports two **notebook delivery modes** (controlled by `notebook.kind` in `deploy/helm/values.yaml`):

| Mode | When to use |
|------|----------------|
| **`Deployment`** (default) | Plain `Deployment` + `Service` + `Route` using the public **Open Data Hub minimal workbench** image (`quay.io/opendatahub/odh-workbench-jupyter-minimal-cpu-py312-ubi9`). Works on any OpenShift cluster — no RHOAI / ODH notebook-controller required. No injected OAuth proxy; configure `notebook.auth.token` if you need browser auth. |
| **`Notebook`** | Kubeflow `kubeflow.org/v1` **`Notebook`** CR. Requires **Red Hat OpenShift AI** (or upstream **Open Data Hub** notebook-controller) installed on the cluster — the chart fails fast with a friendly error if the CRD is missing. Gives you the dashboard workbench experience and OAuth-proxy auth via `notebooks.opendatahub.io/inject-auth`. |

The same chart installs **Redis** for the notebooks in one of three modes (see **`redis.useOtContainerKitOperator`** and **`redis.useRedisEnterpriseOperator`** in `deploy/helm/values.yaml`):

| Mode | When to use |
|------|----------------|
| **Redis Enterprise Operator (REC + REDB)** (default) | `redis.useRedisEnterpriseOperator: true`. The chart creates `RedisEnterpriseCluster` + `RedisEnterpriseDatabase` and wires the notebook to the auto-generated DB password Secret. **OLM** for **redis-enterprise-operator-cert** is **off** by default; use **`make -f deploy/helm/Makefile deploy-all`** or set **`redis.enterprise.olm.enabled: true`** to apply **OperatorGroup** + **Subscription**, or install the operator from OperatorHub first. |
| **OT-CONTAINER-KIT operator + Redis CR** | Set `redis.useOtContainerKitOperator: true` (and `redis.useRedisEnterpriseOperator: false`), run `helm dependency update`, install once (cluster-scoped RBAC). Use if your platform standardizes on this operator. |
| **External Redis** | Both operator flags **`false`**, set **`secrets.redis.url`** to your broker (`validate-secrets` requires a non-empty URL in that case). |

## What this chart deploys — and what it does not

**Always in the Helm release namespace** (default `redis-notebook`, overridable via `NAMESPACE=…`):

- **Notebook workload** — `notebook.enabled` (default on): either a plain **`Deployment`** + **`Service`** + optional **`Route`** (`notebook.kind=Deployment`), or a **`Notebook`** Kubeflow CR (`notebook.kind=Notebook`) for OpenShift AI / ODH workbenches.
- **Workspace PVC**, **ServiceAccount**, **RoleBinding** (namespace `edit` when RBAC is on), **post-upgrade/post-install Job** that clones `notebook.gitSync.repo` and copies **`demo/`** into the workbench root (unless `notebook.gitSync.enabled` is false).
- **Redis** — exactly one path: **Redis Enterprise** `RedisEnterpriseCluster` + `RedisEnterpriseDatabase` (default), **OT** subchart operator + `Redis` CR, or **none** in-cluster with **`secrets.redis.url`** only.

**Optional — Redis Enterprise via OLM** (`redis.enterprise.olm.enabled: true`, e.g. `make deploy-redis-enterprise-olm` or `make deploy-all`):

- **`OperatorGroup`** + **`Subscription`** for **`redis-enterprise-operator-cert`** in the **same namespace as the release** (not cluster-wide). OLM then installs the operator; the chart does **not** ship the operator binary itself.

**Optional — Red Hat OpenShift AI operator via OLM** (`openshiftAI.operator.enabled: true`, e.g. `make deploy-openshift-ai-operator` or `make deploy-all`):

- **`Namespace`** (if `openshiftAI.operator.createNamespace`, default `redhat-ods-operator`), **`OperatorGroup`**, **`Subscription`** for **`rhods-operator`** (`channel`, `source`, etc. from `deploy/helm/values.yaml`). That subscribes the **OpenShift AI / RHOODS operator**; reconciling **DataScienceCluster** / dashboard / notebook-controller features is **operator- and cluster-dependent** after the CSV succeeds — this chart does **not** apply a `DataScienceCluster` CR or pre-configure all RHOAI components.

**Not deployed by this chart**

- **No standalone production API** for the insurance demo — only the workbench and Redis wiring for the notebooks.
- **No automatic full “OpenShift AI product” rollout** beyond the optional **`rhods-operator`** Subscription (cluster admins may still need to approve install plans, configure DSC, GPU nodes, etc.).
- **No Redis Enterprise operator** unless you enable **`redis.enterprise.olm`** or install **`redis-enterprise-operator-cert`** from OperatorHub into the release namespace yourself.
- **No Kubeflow notebook-controller** — `notebook.kind=Notebook` assumes RHOAI/ODH already provides it.

## Prerequisites

- OpenShift cluster with **`oc`** and **`helm`** configured. The default `Deployment` mode runs on any vanilla OpenShift cluster; **only the `Notebook` mode** additionally requires **Red Hat OpenShift AI** (or upstream **Open Data Hub** notebook-controller). Quick check:
  ```bash
  oc get crd notebooks.kubeflow.org   # required only for notebook.kind=Notebook
  ```
- A **workbench image** the cluster can pull. Default is `quay.io/opendatahub/odh-workbench-jupyter-minimal-cpu-py312-ubi9:latest` (publicly pullable, OpenShift-SCC-friendly). For `Notebook` mode on RHOAI, override to the in-cluster image stream, e.g. `image-registry.openshift-image-registry.svc:5000/redhat-ods-applications/tensorflow:2025.2`.
- **Helm 3** with access to `https://ot-container-kit.github.io/helm-charts/` **only if** you enable **`redis.useOtContainerKitOperator`** (then run `make -f deploy/helm/Makefile deps`).
- **Cluster administrator** privileges the first time you install the bundled **redis-operator** subchart (cluster-scoped RBAC). If an OT redis-operator is already installed, keep **`redis.useOtContainerKitOperator: false`** and use **Redis Enterprise** or **external** Redis, or set it **`true`** and coordinate with your admin so you do not duplicate the operator.
- **Redis Enterprise Operator** — when **`redis.useRedisEnterpriseOperator`** is true (default), the chart creates REC/REDB. **OLM** (**`redis.enterprise.olm`**) is **false** by default so `make deploy` does not install the operator; use **`deploy-all`** or set **`redis.enterprise.olm.enabled: true`** to subscribe **redis-enterprise-operator-cert** (needs **`certified-operators`** and permission to create **OperatorGroup** / **Subscription**). If the namespace already has an **OperatorGroup**, set **`redis.enterprise.olm.createOperatorGroup: false`**. The chart fails fast if the `app.redislabs.com` CRDs are missing. Quick check:
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
| `helm/values.yaml` | Notebook, git clone, Redis mode (Enterprise vs OT vs external); non-secret defaults. |
| `helm/values-secret.example.yaml` | Template for **`values-secret.yaml`** (copy locally; gitignored). Holds `secrets.model.*` and optional `secrets.redis.url`. |
| `helm/templates/` | `_helpers.tpl`, `NOTES.txt`, **`notebook/`**, **`redis-enterprise/`** (OLM + REC + REDB), **`openshift-ai/`** (optional Namespace / OperatorGroup / Subscription for `rhods-operator`), **`rbac/`**. |
| `helm/Makefile` | All deploy automation: `help`, `deps`, `lint`, `template`, `check-secrets`, `validate-secrets`, `create-namespace`, `deploy`, OLM variants, `logs-clone`, `undeploy` (see table below). |
| `helm/scripts/validate_secrets.py` | Merges values like Helm and fails on empty/null **`secrets.model.*`** (and **`secrets.redis.url`** when using external Redis only). |

## Makefile commands (reference)

All targets are invoked from the **repository root** with `make -f deploy/helm/Makefile <target>` (or `cd deploy/helm && make <target>`). Common variables: **`NAMESPACE`**, **`RELEASE_NAME`**, **`OPENSHIFT_AI_OPERATOR_NAMESPACE`** (for **`undeploy`** OLM cleanup; default **`redhat-ods-operator`**, match **`openshiftAI.operator.namespace`** in values), **`CHART_DIR`**, **`VALUES_FILE`**, **`VALUES_SECRET_FILE`**, **`TIMEOUT`** (default `10m`), **`HELM_EXTRA_ARGS`** (appended to `helm upgrade` / `helm template`).

| Target | What it runs | OLM / timeouts |
|--------|----------------|-----------------|
| **`help`** | Prints platform (`oc` vs `kubectl`), current variable values, and target list with descriptions. | — |
| **`deps`** | `helm dependency update` on the chart (OT **`redis-operator`** + **`redis`** subcharts). Safe to run every deploy; required before first install if **`redis.useOtContainerKitOperator`** is true. | — |
| **`lint`** | `helm lint` with capability skips so CI clusters without Redis CRDs still lint. | — |
| **`template`** | `helm template` to stdout; uses **`values-secret.yaml`** when the file exists (does **not** run **`validate-secrets`**). | — |
| **`create-namespace`** | `oc new-project` / `oc project` on OpenShift, or `kubectl create namespace` elsewhere. | — |
| **`check-secrets`** | Fails if **`values-secret.yaml`** is missing. | — |
| **`validate-secrets`** | **`check-secrets`** then `scripts/validate_secrets.py` (merged **`secrets.*`** must be non-empty where required). | — |
| **`deploy`** | **`validate-secrets`**, **`deps`**, **`create-namespace`**, then **`helm upgrade --install`** with **`--wait`** and **`TIMEOUT`**. Default **`values.yaml`** leaves **`redis.enterprise.olm.enabled=false`** and **`openshiftAI.operator.enabled=false`**. | Default **`TIMEOUT=10m`**. |
| **`deploy-redis-enterprise-olm`** | Same as **`deploy`** with **`--set redis.enterprise.olm.enabled=true`**. | **`TIMEOUT=25m`**. |
| **`deploy-openshift-ai-operator`** | Same as **`deploy`** with **`--set openshiftAI.operator.enabled=true`** only (Redis Enterprise OLM still follows **`values.yaml`**, usually off). Subscribes **`rhods-operator`** in **`openshiftAI.operator.namespace`** (default **`redhat-ods-operator`**). | **`TIMEOUT=25m`**. |
| **`deploy-all`** | **`deploy`** with **both** Redis Enterprise OLM and OpenShift AI operator flags set **`true`**. | **`TIMEOUT=25m`**. |
| **`deploy-without-redis-enterprise-olm`** | **`deploy`** with **`redis.enterprise.olm.enabled=false`** explicitly (matches stock **`values.yaml`**). | Default **`TIMEOUT`**. |
| **`logs-clone`** | Logs from pods labeled **`app.kubernetes.io/component=notebook-setup`**. | — |
| **`undeploy`** | **`helm uninstall --wait`**, then **`kubectl`/`oc` delete** of **`Subscription`** and **`OperatorGroup`** still matching this release’s Helm labels (`app.kubernetes.io/instance=RELEASE_NAME`, `managed-by=Helm`, component `redis-enterprise-olm` or `openshift-ai-operator`) in **`NAMESPACE`** and **`OPENSHIFT_AI_OPERATOR_NAMESPACE`** (default **redhat-ods-operator**). Catches OLM objects Helm sometimes leaves when uninstalling cross-namespace resources. | Does **not** delete the release **`NAMESPACE`** or **`redhat-ods-operator`** itself. CSV/operator pods may disappear shortly after the **`Subscription`** is removed (OLM). Override **`OPENSHIFT_AI_OPERATOR_NAMESPACE`** if your values differ. |

**Quick start (minimal):**

```bash
cp deploy/helm/values-secret.example.yaml deploy/helm/values-secret.yaml
# Edit deploy/helm/values-secret.yaml — set secrets.model.apiKey (and anything else you need)

make -f deploy/helm/Makefile help
make -f deploy/helm/Makefile deploy
```

**Optional — let the chart install operators via OLM** (long-running; watch CSVs):

```bash
make -f deploy/helm/Makefile deploy-redis-enterprise-olm   # Redis Enterprise operator Subscription in release namespace only
make -f deploy/helm/Makefile deploy-openshift-ai-operator # rhods-operator Subscription in redhat-ods-operator (defaults)
make -f deploy/helm/Makefile deploy-all                     # both of the above
```

Override namespace / release:

```bash
make -f deploy/helm/Makefile deploy NAMESPACE=my-project RELEASE_NAME=my-release
```

## Quick deploy (Helm only)

**Redis Enterprise Operator (REC + REDB) — default.** Plain **`make deploy`** creates REC/REDB only; install **redis-enterprise-operator-cert** from OperatorHub into the namespace first, or use **`make -f deploy/helm/Makefile deploy-all`** to let the chart apply **OperatorGroup** + **Subscription** as well.

```bash
cp ./deploy/helm/values-secret.example.yaml ./deploy/helm/values-secret.yaml
# Edit values-secret.yaml (at least secrets.model.apiKey)

oc new-project redis-notebook           # or choose your own namespace
make -f deploy/helm/Makefile deploy
# Chart-managed OLM (see Makefile reference above):
# make -f deploy/helm/Makefile deploy-redis-enterprise-olm
# make -f deploy/helm/Makefile deploy-openshift-ai-operator
# make -f deploy/helm/Makefile deploy-all
```

The chart will refuse to render if the `app.redislabs.com` CRDs are not registered on the cluster. With chart-managed OLM, wait for the **CSV** to reach **Succeeded** (`oc get csv -n redis-notebook -w`) before `rec` / `redb` reconcile. Tune cluster size / database resources via `redis.enterprise.cluster.*` and `redis.enterprise.database.*` in `values.yaml`.

**OT operator + Redis CR**:

```bash
helm dependency update ./deploy/helm
helm upgrade --install redis-notebook ./deploy/helm \
  --namespace redis-notebook \
  --values ./deploy/helm/values.yaml \
  --values ./deploy/helm/values-secret.yaml \
  --set redis.useRedisEnterpriseOperator=false \
  --set redis.useOtContainerKitOperator=true \
  --wait --timeout 10m
```

**External Redis only** (no in-cluster Redis; set a real broker in **`values-secret.yaml`** → **`secrets.redis.url`**):

```bash
helm upgrade --install redis-notebook ./deploy/helm \
  --namespace redis-notebook \
  --values ./deploy/helm/values.yaml \
  --values ./deploy/helm/values-secret.yaml \
  --set redis.useRedisEnterpriseOperator=false \
  --set redis.useOtContainerKitOperator=false \
  --wait --timeout 10m
```

If **redis-operator** is already on the cluster, avoid duplicate cluster RBAC: keep **`redis.useOtContainerKitOperator: false`** and use **Redis Enterprise** or **external** Redis, or install only the `redisData` instance from a shared operator (advanced — not split in this chart).

## What the chart creates

**When `redis.useOtContainerKitOperator` is true**, the **[OT-CONTAINER-KIT redis-operator](https://github.com/OT-CONTAINER-KIT/redis-operator)** subchart installs the operator Deployment plus **cluster-scoped** RBAC (unless already satisfied), and the **`redisData`** subchart creates a **`Redis`** custom resource for a **standalone** Redis 7 instance.

**When `redis.useRedisEnterpriseOperator` is true**, the chart creates a **`RedisEnterpriseCluster`** (`app.redislabs.com/v1`, default 3 nodes with persistence) and a **`RedisEnterpriseDatabase`** (`app.redislabs.com/v1alpha1`, single shard with replication by default). When **`redis.enterprise.olm.enabled`** is **true** (e.g. **`make deploy-all`**), it also creates an **OperatorGroup** and **Subscription** so OLM installs **redis-enterprise-operator-cert** in the release namespace. The operator reconciles REC/REDB into a Redis Enterprise StatefulSet, an internal admin service, and a per-database service named after `redis.enterprise.database.name` (default `redb`). The operator also creates a Secret named **`redb-<database.name>`** holding the auto-generated `password`, `port`, and `service_names`; the notebook deployment mounts `password` and `port` via `secretKeyRef` and composes `REDIS_URL` with Kubernetes `$(VAR)` interpolation.

**When both `redis.useOtContainerKitOperator` and `redis.useRedisEnterpriseOperator` are false**, no in-cluster Redis is created; the notebook **`REDIS_URL`** comes from **`secrets.redis.url`** (must be non-empty; **`validate-secrets`** enforces this).

**When `openshiftAI.operator.enabled` is true** (e.g. **`make deploy-openshift-ai-operator`** or **`make deploy-all`**), the chart may create a **`Namespace`**, **`OperatorGroup`**, and **`Subscription`** for **`rhods-operator`** in **`openshiftAI.operator.namespace`** (default **`redhat-ods-operator`**), per **`openshiftAI.operator.createNamespace`**, **`createOperatorGroup`**, and **`subscription.*`** in `values.yaml`. That is only the **operator subscription**; it does not replace cluster admin steps for **DataScienceCluster** or other RHOAI configuration.

Other resources:

1. **ServiceAccount** and **RoleBinding** to the cluster **`edit`** role so the workbench workload can use the namespace as expected.
2. **PersistentVolumeClaim** — read-write-once workspace for `/opt/app-root/src` (annotation keeps the PVC across uninstall if you rely on that policy).
3. **Notebook workload** — depends on `notebook.kind`:
   - `Deployment` (default): a plain `Deployment` + `ClusterIP` `Service` + OpenShift `Route` (edge TLS) using the configured image, probes, and a `/dev/shm` emptyDir.
   - `Notebook`: a `kubeflow.org/v1` `Notebook` CR; the RHOAI / ODH notebook-controller reconciles it into a `StatefulSet` + `Service` + `Route` with an injected OAuth proxy.
4. **Job** (post-install / post-upgrade hook) — waits for the PVC, clones `notebook.gitSync.repo` (optional branch), copies **`demo/`** into the workspace root, then exits. Notebooks appear under **`demo/notebooks`** inside the workspace (i.e. `/opt/app-root/src/demo/notebooks` in the container).

The notebook **`REDIS_URL`** environment variable is set from **`redis-notebook.redisUrl`** in templates: Redis Enterprise (with `$(REDIS_PASSWORD)` / `$(REDIS_PORT)`), OT-operator service DNS, or **`secrets.redis.url`** for external-only.

Disable the clone Job by setting `notebook.gitSync.enabled: false` in a custom values file.

## Demo notebooks — runtime expectations

The `demo/notebooks` flow (and `demo/shared/insurance_bot.py`) expect:

| Item | Notes |
|------|--------|
| **OpenAI-compatible LLM** | `MODEL_API_KEY` (required), `MODEL_ENDPOINT` (default `https://api.openai.com`), `SIMPLE_MODEL_NAME` / `COMPLEX_MODEL_NAME` with defaults. The chart injects these from `values.yaml` layered with **`values-secret.yaml`** (`secrets.model.*`). |
| **Redis URL** | `REDIS_URL` — Redis Enterprise or OT in-cluster URL, or `secrets.redis.url` when external. Use a **Redis Stack**–capable or Enterprise endpoint for **redisvl** / notebook **02** (search modules). |
| **`.env` in repo root** | Notebooks call `load_dotenv(REPO_ROOT / ".env")` with `REPO_ROOT` resolved from `demo/notebooks`; chart env vars still apply for missing keys. |
| **`TOKENIZERS_PARALLELISM`** | Set to `false` inside `02_router_cache.ipynb` to silence Hugging Face tokenizer fork warnings. |
| **Python dependencies** | Install from `demo/scripts/requirements.txt` in the workbench (or bake into a custom image). RHOAI / Red Hat curated PyPI may omit **`redisvl`** — use `--extra-index-url https://pypi.org/simple` or rely on **`notebook.pipExtraIndexUrl`** (default) so the chart sets **`PIP_EXTRA_INDEX_URL`** on the pod. |

**External OSS Redis:** If **`secrets.redis.url`** points at plain `redis` without modules, notebook **02** (redisvl) needs **RediSearch** / Stack-style capabilities — use **Redis Enterprise**, **Redis Stack** elsewhere, or an OT deployment that exposes those modules.

## Important configuration (`values.yaml`)

| Area | Keys | Notes |
|------|------|--------|
| OpenShift | `global.openshift` | Currently informational; templates render on any cluster (`Route` is gated on the OpenShift Route CRD via `Capabilities.APIVersions`). |
| OpenShift AI OLM | `openshiftAI.operator.{enabled,namespace,createNamespace,createOperatorGroup,operatorGroupName,skipCapabilityCheck,subscription.*}` | Default **`enabled: false`**. When **`true`**, chart applies **`Subscription`** (and optional **`Namespace`** / **`OperatorGroup`**) for **`rhods-operator`** in **`openshiftAI.operator.namespace`** (default **`redhat-ods-operator`**). Use **`make deploy-openshift-ai-operator`** or **`deploy-all`**. |
| Notebook mode | `notebook.kind` | `Deployment` (default, no RHOAI required) or `Notebook` (Kubeflow CR — needs RHOAI / ODH). |
| Redis mode | `redis.useOtContainerKitOperator`, `redis.useRedisEnterpriseOperator` | OT operator+CR vs Redis Enterprise REC+REDB vs external (`secrets.redis.url` when both flags are false). At most one operator flag should be true. |
| Redis Enterprise | `redis.enterprise.cluster.*`, `redis.enterprise.database.*`, `redis.enterprise.olm.{enabled,createOperatorGroup,operatorGroupName,skipCapabilityCheck,subscription.*}` | Only when `redis.useRedisEnterpriseOperator: true`. **OLM** (`redis.enterprise.olm`, **default off**) installs **redis-enterprise-operator-cert** when **`enabled: true`** (**`make deploy-redis-enterprise-olm`** or **`deploy-all`**). Defaults to a 3-node cluster with persistence and a single-shard replicated database `redb`. The notebook reads `password` / `port` from the operator-generated `redb-<database.name>` Secret unless you override `passwordSecretName`. |
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
| External Redis | `secrets.redis.url` | No chart-managed Redis. Set **`redis.useOtContainerKitOperator: false`** and **`redis.useRedisEnterpriseOperator: false`**; **`secrets.redis.url`** must be a real broker URL (validated at deploy). |

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
- **Redis Enterprise mode**: with **`redis.enterprise.olm.enabled: true`** (e.g. **`make deploy-redis-enterprise-olm`** or **`make deploy-all`**), the chart creates the **Subscription** in the **release** namespace; wait until **`oc get csv -n <release-namespace>`** shows **Succeeded** so `rec` / `redb` reconcile and the **`redb-<database.name>`** Secret appears. With OLM **off** (default **`make deploy`**), install **redis-enterprise-operator-cert** from OperatorHub into the namespace first. If `rec`/`redb` were created before the CSV succeeded, delete those CRs or reinstall after the operator is healthy. The notebook Deployment stays in **Init** until the Secret exists. Inspect credentials with `oc get secret redb-<database.name> -n <namespace> -o yaml`.
- **OpenShift AI operator** (when **`openshiftAI.operator.enabled: true`**): watch the CSV in the **operator** namespace (default **`redhat-ods-operator`**), e.g. **`oc get csv,subscription -n redhat-ods-operator -w`**, until the **Red Hat OpenShift AI** operator install succeeds. The workbench **`Notebook`** CR mode still requires a healthy RHOAI/ODH control plane and **`notebooks.kubeflow.org`** on the cluster.
- If the clone Job fails (network, private repo, or volume contention), check **`make -f deploy/helm/Makefile logs-clone`** or inspect the Job pods in the namespace. With **ReadWriteOnce** storage, only one pod can mount the PVC at a time; if the notebook pod already holds the claim, the clone Job may not schedule until that pod releases the volume—stop the notebook workload temporarily if you need to re-run the clone, or adjust storage / workflow for your environment.

## Remove the release

```bash
make -f deploy/helm/Makefile undeploy
# or
helm uninstall redis-notebook --namespace redis-notebook
```

**`make undeploy`** runs **`helm uninstall --wait`**, then deletes any remaining chart-labeled **`Subscription`** / **`OperatorGroup`** for this **`RELEASE_NAME`** in the release namespace and in **`OPENSHIFT_AI_OPERATOR_NAMESPACE`** (see Makefile). OLM then tears down CSV/operator workloads; that can take a short time after the **`Subscription`** disappears. The release namespace, **`redhat-ods-operator`**, and the workspace PVC are **not** deleted automatically. On shared clusters, removing **`rhods-operator`** affects everyone using that operator — coordinate with your platform team.
