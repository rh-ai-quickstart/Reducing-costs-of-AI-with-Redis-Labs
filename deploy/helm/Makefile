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
# Appended to helm upgrade|template (e.g. --set openshiftAI.operator.enabled=true).
HELM_EXTRA_ARGS ?=

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
	@echo "  HELM_EXTRA_ARGS=$(HELM_EXTRA_ARGS)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Targets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

.PHONY: deps
deps: ## helm dependency update (OT subcharts; only needed when redis.useOtContainerKitOperator is true)
	helm dependency update $(CHART_DIR)

.PHONY: lint
lint: ## helm lint (skips REC/REDB CRD + OLM preflight; lint has no --api-versions)
	helm lint $(CHART_DIR) --set redis.skipCapabilityCheck=true --set redis.enterprise.olm.skipCapabilityCheck=true

.PHONY: template
template: ## Render manifests to stdout (adds values-secret when file exists; no validate-secrets)
	@if [ -f "$(VALUES_SECRET_FILE)" ]; then \
		helm template $(RELEASE_NAME) $(CHART_DIR) --namespace $(NAMESPACE) \
			--values $(VALUES_FILE) \
			--values $(VALUES_SECRET_FILE) \
			--set redis.skipCapabilityCheck=true \
			--set redis.enterprise.olm.skipCapabilityCheck=true \
			$(HELM_EXTRA_ARGS); \
	else \
		helm template $(RELEASE_NAME) $(CHART_DIR) --namespace $(NAMESPACE) \
			--values $(VALUES_FILE) \
			--set redis.skipCapabilityCheck=true \
			--set redis.enterprise.olm.skipCapabilityCheck=true \
			$(HELM_EXTRA_ARGS); \
	fi

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
		--timeout $(TIMEOUT) \
		$(HELM_EXTRA_ARGS)
	@echo "Done. Pods: $(KUBECTL) get pods -n $(NAMESPACE)"

.PHONY: deploy-openshift-ai-operator
deploy-openshift-ai-operator: ## deploy + OLM Subscription/OperatorGroup for rhods-operator (OpenShift AI)
	@$(MAKE) -f "$(abspath $(lastword $(MAKEFILE_LIST)))" deploy \
		HELM_EXTRA_ARGS='--set openshiftAI.operator.enabled=true'

.PHONY: deploy-without-redis-enterprise-olm
deploy-without-redis-enterprise-olm: ## deploy but skip chart-managed Redis Enterprise OLM (operator already installed)
	@$(MAKE) -f "$(abspath $(lastword $(MAKEFILE_LIST)))" deploy \
		HELM_EXTRA_ARGS='--set redis.enterprise.olm.enabled=false'

.PHONY: logs-clone
logs-clone: ## Logs from the git-clone post-install Job pods (if any)
	@$(KUBECTL) logs -n $(NAMESPACE) -l app.kubernetes.io/component=notebook-setup --tail=200 --all-containers=true 2>/dev/null || \
		echo "No clone job pods found in $(NAMESPACE)."

.PHONY: undeploy
undeploy: ## helm uninstall (namespace left in place)
	helm uninstall $(RELEASE_NAME) --namespace $(NAMESPACE) 2>/dev/null || true
	@echo "Release removed (PVC may remain if policy=keep)."