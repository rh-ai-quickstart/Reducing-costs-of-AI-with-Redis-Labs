# OpenShift AI notebook Helm chart — thin wrapper around helm/oc
# 
# Usage:
#   make -f deploy/helm/Makefile help
#   make -f deploy/helm/Makefile deploy
# Or from this directory:
#   cd deploy/helm && make deploy

# Strip trailing slash from $(dir ...) so paths like $(CHART_DIR)/values.yaml stay clean.
ROOT_DIR := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
CHART_DIR ?= $(ROOT_DIR)
VALUES_FILE ?= $(CHART_DIR)/values.yaml
VALUES_SECRET_FILE ?= $(CHART_DIR)/values-secret.yaml

NAMESPACE ?= redis-notebook
RELEASE_NAME ?= redis-notebook
# Label selectors for chart-managed OLM objects (must match chart templates).
REDIS_OLM_SELECTOR := app.kubernetes.io/instance=$(RELEASE_NAME),app.kubernetes.io/managed-by=Helm,app.kubernetes.io/component=redis-enterprise-olm
AI_OLM_SELECTOR := app.kubernetes.io/instance=$(RELEASE_NAME),app.kubernetes.io/managed-by=Helm,app.kubernetes.io/component=openshift-ai-operator
# Redis Enterprise names for uninstall (defaults match deploy/helm/values.yaml).
REDIS_ENTERPRISE_CLUSTER_NAME ?= rec
REDIS_ENTERPRISE_DATABASE_NAME ?= redb
REDIS_ENTERPRISE_SUBSCRIPTION_NAME ?= redis-enterprise-operator-cert
REDIS_ENTERPRISE_OPERATOR_GROUP_NAME ?= redis-enterprise-operator-group
REDIS_UNDEPLOY_WAIT ?= 120
# Used by uninstall to remove chart-managed OpenShift AI OLM objects (must match values.yaml openshiftAI.operator.namespace).
OPENSHIFT_AI_OPERATOR_NAMESPACE ?= redhat-ods-operator
TIMEOUT ?= 10m
# Appended to helm upgrade|template (e.g. make deploy-all sets Redis OLM + OpenShift AI).
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

.PHONY: deploy-all
deploy-all: ## deploy + Redis Enterprise OLM
	@echo "Deploying Redis Enterprise OLM + OpenShift AI OLM..."
	@$(MAKE) -f "$(abspath $(lastword $(MAKEFILE_LIST)))" deploy \
		TIMEOUT=25m \
		HELM_EXTRA_ARGS='--set redis.enterprise.olm.enabled=true'

.PHONY: deploy-without-redis-enterprise-olm
deploy-without-redis-enterprise-olm: ## deploy with redis.enterprise.olm.enabled=false (same as default values)
	@$(MAKE) -f "$(abspath $(lastword $(MAKEFILE_LIST)))" deploy \
		HELM_EXTRA_ARGS='--set redis.enterprise.olm.enabled=false'

.PHONY: deploy-with-roi-dashboard
deploy-with-roi-dashboard: ## deploy notebook + ROI dashboard + RAK worker
	@$(MAKE) -f "$(abspath $(lastword $(MAKEFILE_LIST)))" deploy \
		HELM_EXTRA_ARGS='--set roiDashboard.enabled=true --set insuranceWorker.enabled=true $(HELM_EXTRA_ARGS)'

.PHONY: deploy-dashboard-only
deploy-dashboard-only: ## deploy Redis + ROI dashboard + RAK worker (no notebook)
	@$(MAKE) -f "$(abspath $(lastword $(MAKEFILE_LIST)))" deploy \
		HELM_EXTRA_ARGS='--set notebook.enabled=false --set roiDashboard.enabled=true --set insuranceWorker.enabled=true $(HELM_EXTRA_ARGS)'

.PHONY: route-roi-dashboard
route-roi-dashboard: ## Print the OpenShift Route URL for the ROI dashboard
	@$(KUBECTL) get route -n $(NAMESPACE) -l app.kubernetes.io/instance=$(RELEASE_NAME),app.kubernetes.io/component=roi-dashboard -o jsonpath='https://{.items[0].spec.host}{"\n"}' 2>/dev/null || \
		echo "No Route found. Try: make -f deploy/helm/Makefile logs-roi-dashboard NAMESPACE=$(NAMESPACE)"

.PHONY: logs-roi-dashboard
logs-roi-dashboard: ## Logs from the roi-dashboard container
	@POD=$$($(KUBECTL) get pods -n $(NAMESPACE) -l app.kubernetes.io/instance=$(RELEASE_NAME),app.kubernetes.io/component=roi-dashboard -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$POD" ]; then \
		echo "No roi-dashboard pod found in $(NAMESPACE) (is roiDashboard.enabled=true?)."; \
	else \
		$(KUBECTL) logs -n $(NAMESPACE) "$$POD" -c roi-dashboard --tail=200 -f; \
	fi

.PHONY: logs-insurance-worker
logs-insurance-worker: ## Logs from the RAK insurance worker container
	@POD=$$($(KUBECTL) get pods -n $(NAMESPACE) -l app.kubernetes.io/instance=$(RELEASE_NAME),app.kubernetes.io/component=insurance-worker -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$POD" ]; then \
		echo "No insurance-worker pod found in $(NAMESPACE) (is insuranceWorker.enabled=true?)."; \
	else \
		$(KUBECTL) logs -n $(NAMESPACE) "$$POD" -c insurance-worker --tail=200 -f; \
	fi

.PHONY: logs-roi-clone
logs-roi-clone: ## Logs from git-sync-demo init container on the roi-dashboard pod
	@POD=$$($(KUBECTL) get pods -n $(NAMESPACE) -l app.kubernetes.io/instance=$(RELEASE_NAME),app.kubernetes.io/component=roi-dashboard -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$POD" ]; then \
		echo "No roi-dashboard pod found in $(NAMESPACE) (is roiDashboard.enabled=true?)."; \
	else \
		$(KUBECTL) logs -n $(NAMESPACE) "$$POD" -c git-sync-demo --tail=200 2>/dev/null || \
		echo "No git-sync-demo init logs (gitSync disabled or init not run yet). Pod: $$POD"; \
	fi

.PHONY: logs-clone
logs-clone: ## Logs from git-sync-demo init container on the notebook pod
	@POD=$$($(KUBECTL) get pods -n $(NAMESPACE) -l app.kubernetes.io/instance=$(RELEASE_NAME),app.kubernetes.io/component=notebook -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$POD" ]; then \
		echo "No notebook pod found in $(NAMESPACE)."; \
	else \
		$(KUBECTL) logs -n $(NAMESPACE) "$$POD" -c git-sync-demo --tail=200 2>/dev/null || \
		echo "No git-sync-demo init logs (gitSync disabled or init not run yet). Pod: $$POD"; \
	fi

.PHONY: uninstall
uninstall: ## helm uninstall --wait + Redis Enterprise (REDB/REC/OLM) + OpenShift AI OLM cleanup
	@echo "Uninstall $(RELEASE_NAME) in $(NAMESPACE)..."
	@echo "Removing Redis Enterprise database and cluster (if present)..."
	@$(KUBECTL) delete redisenterprisedatabases.app.redislabs.com "$(REDIS_ENTERPRISE_DATABASE_NAME)" -n "$(NAMESPACE)" --ignore-not-found --wait=false
	@$(KUBECTL) delete redisenterpriseclusters.app.redislabs.com "$(REDIS_ENTERPRISE_CLUSTER_NAME)" -n "$(NAMESPACE)" --ignore-not-found --wait=false
	@echo "Waiting up to $(REDIS_UNDEPLOY_WAIT)s for REC/REDB teardown..."
	@i=0; while [ $$i -lt $(REDIS_UNDEPLOY_WAIT) ]; do \
		rec=$$($(KUBECTL) get redisenterpriseclusters.app.redislabs.com "$(REDIS_ENTERPRISE_CLUSTER_NAME)" -n "$(NAMESPACE)" --ignore-not-found -o name 2>/dev/null); \
		redb=$$($(KUBECTL) get redisenterprisedatabases.app.redislabs.com "$(REDIS_ENTERPRISE_DATABASE_NAME)" -n "$(NAMESPACE)" --ignore-not-found -o name 2>/dev/null); \
		[ -z "$$rec" ] && [ -z "$$redb" ] && break; \
		i=$$((i + 5)); sleep 5; \
	done
	@rec=$$($(KUBECTL) get redisenterpriseclusters.app.redislabs.com "$(REDIS_ENTERPRISE_CLUSTER_NAME)" -n "$(NAMESPACE)" --ignore-not-found -o name 2>/dev/null); \
	if [ -n "$$rec" ]; then \
		echo "REC still present; clearing finalizers so teardown can continue..."; \
		$(KUBECTL) patch redisenterpriseclusters.app.redislabs.com "$(REDIS_ENTERPRISE_CLUSTER_NAME)" -n "$(NAMESPACE)" --type=merge -p '{"metadata":{"finalizers":[]}}' --ignore-not-found || true; \
		$(KUBECTL) delete redisenterpriseclusters.app.redislabs.com "$(REDIS_ENTERPRISE_CLUSTER_NAME)" -n "$(NAMESPACE)" --ignore-not-found --wait=false || true; \
	fi
	@helm uninstall "$(RELEASE_NAME)" --namespace "$(NAMESPACE)" --wait || true
	@echo "Removing Redis Enterprise operator (OLM Subscription/OperatorGroup) in $(NAMESPACE)..."
	@$(KUBECTL) delete subscriptions.operators.coreos.com -n "$(NAMESPACE)" -l "$(REDIS_OLM_SELECTOR)" --ignore-not-found
	@$(KUBECTL) delete subscriptions.operators.coreos.com "$(REDIS_ENTERPRISE_SUBSCRIPTION_NAME)" -n "$(NAMESPACE)" --ignore-not-found
	@$(KUBECTL) delete operatorgroups.operators.coreos.com -n "$(NAMESPACE)" -l "$(REDIS_OLM_SELECTOR)" --ignore-not-found
	@$(KUBECTL) delete operatorgroups.operators.coreos.com "$(REDIS_ENTERPRISE_OPERATOR_GROUP_NAME)" -n "$(NAMESPACE)" --ignore-not-found
	@echo "Removing Redis Enterprise operator CSV and workloads (OLM may leave Failed CSVs behind)..."
	@sleep 5
	@$(KUBECTL) delete clusterserviceversion.operators.coreos.com -n "$(NAMESPACE)" -l "operators.coreos.com/$(REDIS_ENTERPRISE_SUBSCRIPTION_NAME).$(NAMESPACE)" --ignore-not-found
	@for csv in $$($(KUBECTL) get clusterserviceversion.operators.coreos.com -n "$(NAMESPACE)" -o name 2>/dev/null | grep redis-enterprise-operator || true); do \
		echo "Deleting $$csv"; \
		$(KUBECTL) delete "$$csv" -n "$(NAMESPACE)" --ignore-not-found --wait=false; \
	done
	@$(KUBECTL) delete deployment redis-enterprise-operator -n "$(NAMESPACE)" --ignore-not-found --wait=false
	@$(KUBECTL) delete service redis-enterprise-operator-service -n "$(NAMESPACE)" --ignore-not-found
	@$(KUBECTL) delete subscriptions.operators.coreos.com -n "$(OPENSHIFT_AI_OPERATOR_NAMESPACE)" -l "$(AI_OLM_SELECTOR)" --ignore-not-found
	@$(KUBECTL) delete operatorgroups.operators.coreos.com -n "$(OPENSHIFT_AI_OPERATOR_NAMESPACE)" -l "$(AI_OLM_SELECTOR)" --ignore-not-found
	@echo "Done. Release namespace was not deleted; workspace PVC may remain (chart policy=keep)."
	@echo "Redis Enterprise operator Subscription, CSV, and deployment removed from $(NAMESPACE) (re-check: oc get csv,pods -n $(NAMESPACE) | grep -i redis)."
	@echo "OpenShift AI namespace $(OPENSHIFT_AI_OPERATOR_NAMESPACE) is left in place (shared cluster scope)."