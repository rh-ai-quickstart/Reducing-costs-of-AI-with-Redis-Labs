# OpenShift AI notebook Helm chart — thin wrapper around helm/oc
#
# Usage (from anywhere):
#   make -f deploy/helm/Makefile deploy
# Or:
#   cd deploy/helm && make deploy

# Strip trailing slash from $(dir ...) so paths like $(CHART_DIR)/values.yaml stay clean.
ROOT_DIR := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
CHART_DIR ?= $(ROOT_DIR)
VALUES_FILE ?= $(CHART_DIR)/values.yaml
VALUES_SECRET_FILE ?= $(CHART_DIR)/values-secret.yaml

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
	@echo "  VALUES_FILE=$(VALUES_FILE)"
	@echo "  VALUES_SECRET_FILE=$(VALUES_SECRET_FILE)  (required for deploy)"
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

.PHONY: check-secrets
check-secrets: ## Fail if values-secret.yaml is missing (required for deploy)
	@if [ ! -f "$(VALUES_SECRET_FILE)" ]; then \
		echo "error: $(VALUES_SECRET_FILE) not found." >&2; \
		echo "Create it before deploy, e.g.:" >&2; \
		echo "  cp $(CHART_DIR)/values-secret.example.yaml $(VALUES_SECRET_FILE)" >&2; \
		echo "Then edit $(VALUES_SECRET_FILE) and set secrets.model.apiKey (and other overrides as needed)." >&2; \
		exit 1; \
	fi

.PHONY: validate-secrets
validate-secrets: check-secrets ## Fail if merged values have null/empty required secrets.* fields
	python3 "$(CHART_DIR)/scripts/validate_secrets.py" "$(VALUES_FILE)" "$(VALUES_SECRET_FILE)"

.PHONY: deploy
deploy: validate-secrets deps create-namespace ## validate secrets + helm upgrade --install
	helm upgrade --install $(RELEASE_NAME) $(CHART_DIR) \
		--namespace $(NAMESPACE) \
		--values $(VALUES_FILE) \
		--values $(VALUES_SECRET_FILE) \
		--wait \
		--timeout $(TIMEOUT)
	@echo "Done. Pods: $(KUBECTL) get pods -n $(NAMESPACE)"

.PHONY: logs-clone
logs-clone: ## Logs from the notebook git-sync init container (same pod as the workbench; no separate Job)
	@POD=$$($(KUBECTL) get pods -n $(NAMESPACE) --no-headers -o name 2>/dev/null | grep -- '-notebook-' | head -1 | sed 's|^pod/||'); \
	if [ -z "$$POD" ]; then echo "No notebook pod name containing -notebook- in $(NAMESPACE)."; exit 1; fi; \
	$(KUBECTL) logs -n $(NAMESPACE) "$$POD" -c git-sync-demo --tail=200 2>/dev/null || \
		$(KUBECTL) logs -n $(NAMESPACE) "$$POD" --tail=200 --all-containers=true

.PHONY: undeploy
undeploy: ## helm uninstall (namespace left in place)
	helm uninstall $(RELEASE_NAME) --namespace $(NAMESPACE) 2>/dev/null || true
	@echo "Release removed (PVC may remain if policy=keep)."