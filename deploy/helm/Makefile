# OpenShift AI notebook Helm chart — thin wrapper around helm/oc
#
# Usage (from anywhere):
#   make -f deploy/helm/Makefile deploy
# Or:
#   cd deploy/helm && make deploy

ROOT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
CHART_DIR ?= $(ROOT_DIR)
VALUES_FILE ?= $(CHART_DIR)/values.yaml

NAMESPACE ?= redis-notebook
RELEASE_NAME ?= redis-notebook
TIMEOUT ?= 10m

KUBECTL := $(shell command -v oc 2>/dev/null)
ifndef KUBECTL
	KUBECTL := kubectl
	PLATFORM := kubernetes
else
	PLATFORM := openshift
endif

.PHONY: help
help: ## Show targets and current settings
	@echo "Redis notebook (OpenShift) — $(PLATFORM), CLI=$(KUBECTL)"
	@echo "  NAMESPACE=$(NAMESPACE)  RELEASE_NAME=$(RELEASE_NAME)"
	@echo "  CHART_DIR=$(CHART_DIR)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Targets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

.PHONY: deps
deps: ## helm dependency update (OT subcharts; only needed when redis.useOtContainerKitOperator is true)
	helm dependency update $(CHART_DIR)

.PHONY: lint
lint: ## helm lint
	helm lint $(CHART_DIR)

.PHONY: template
template: ## Render manifests to stdout (same namespace as deploy)
	helm template $(RELEASE_NAME) $(CHART_DIR) --namespace $(NAMESPACE)

.PHONY: create-namespace
create-namespace: ## Create project/namespace
	@if [ "$(PLATFORM)" = "openshift" ]; then \
		oc new-project $(NAMESPACE) 2>/dev/null || oc project $(NAMESPACE); \
	else \
		$(KUBECTL) create namespace $(NAMESPACE) 2>/dev/null || true; \
	fi

.PHONY: deploy
deploy: deps create-namespace ## helm dependency update + upgrade --install
	helm upgrade --install $(RELEASE_NAME) $(CHART_DIR) \
		--namespace $(NAMESPACE) \
		--values $(VALUES_FILE) \
		--wait \
		--timeout $(TIMEOUT)
	@echo "Done. Pods: $(KUBECTL) get pods -n $(NAMESPACE)"

.PHONY: logs-clone
logs-clone: ## Logs from the git-clone post-install Job pods (if any)
	@$(KUBECTL) logs -n $(NAMESPACE) -l app.kubernetes.io/component=notebook-setup --tail=200 --all-containers=true 2>/dev/null || \
		echo "No clone job pods found in $(NAMESPACE)."

.PHONY: undeploy
undeploy: ## helm uninstall (namespace left in place)
	helm uninstall $(RELEASE_NAME) --namespace $(NAMESPACE) 2>/dev/null || true
	@echo "Release removed (PVC may remain if policy=keep)."