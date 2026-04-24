# Deploy — OpenShift AI notebook

This folder contains a small **Helm chart** that provisions an **OpenShift AI (RHOAI) Kubeflow `Notebook`** with a persistent workspace and a **post-install Job** that clones this repository and copies the **`demo/`** tree into the notebook’s work directory so you can run the quickstart notebooks from the dashboard.

## Prerequisites

- OpenShift cluster with **OpenShift AI** (or equivalent **OpenShift Data Science** / **Kubeflow Notebook** controller) installed.
- **`oc`** and **`helm`** configured for the cluster.
- A **workbench image** available in the cluster (default in `values.yaml` pulls from the internal OpenShift registry path `redhat-ods-applications/tensorflow`, which is typical on RHOAI).

## Layout

| Path | Purpose |
|------|---------|
| `helm/Chart.yaml` | Chart metadata (`redis-notebook`). |
| `helm/values.yaml` | Defaults for notebook image, PVC, resources, and git clone. |
| `helm/templates/` | Kubernetes / OpenShift manifests (Notebook, PVC, RBAC, clone Job). |
| `helm/Makefile` | Optional shortcuts for lint, template, deploy, and undeploy. |

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

- **`lint`** — `helm lint` on the chart.
- **`template`** — render manifests without applying.
- **`deploy`** — create project/namespace (OpenShift: `oc new-project` or `oc project`) then `helm upgrade --install --wait`.
- **`undeploy`** — `helm uninstall` (namespace is not deleted; the PVC may remain because of `helm.sh/resource-policy: keep` on the PVC).

## Quick deploy (Helm only)

```bash
oc new-project redis-notebook   # or choose your own namespace
helm upgrade --install redis-notebook ./deploy/helm \
  --namespace redis-notebook \
  --values ./deploy/helm/values.yaml \
  --wait --timeout 10m
```

## What the chart creates

1. **ServiceAccount** and **RoleBinding** to the cluster **`edit`** role (pre-install hooks) so the workbench workload can use the namespace as expected.
2. **PersistentVolumeClaim** — read-write-once workspace for `/opt/app-root/src` (annotation keeps the PVC across uninstall if you rely on that policy).
3. **`Notebook`** (`kubeflow.org/v1`) — Jupyter-compatible workbench using the configured image, probes, and optional `/dev/shm` emptyDir.
4. **Job** (post-install / post-upgrade hook) — waits for the PVC, clones `notebook.gitSync.repo` (optional branch), copies **`demo/`** into the workspace root, then exits. Notebooks appear under **`demo/notebooks`** inside the workspace (i.e. `/opt/app-root/src/demo/notebooks` in the container).

Disable the clone Job by setting `notebook.gitSync.enabled: false` in a custom values file.

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
