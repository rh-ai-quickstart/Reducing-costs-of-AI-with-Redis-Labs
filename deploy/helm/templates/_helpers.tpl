{{- define "redis-notebook.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "redis-notebook.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "redis-notebook.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "redis-notebook.labels" -}}
helm.sh/chart: {{ include "redis-notebook.chart" . }}
{{ include "redis-notebook.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "redis-notebook.selectorLabels" -}}
app.kubernetes.io/name: {{ include "redis-notebook.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "redis-notebook.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "redis-notebook.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Redis connection URL for notebooks:
- Redis Enterprise: interpolated URL with $(REDIS_PASSWORD) / $(REDIS_PORT) (see redisEnv)
- OT operator path: Redis CR service (name from redisData.redisStandalone.name or release name)
- Else: secrets.redis.url (external)
*/}}
{{- define "redis-notebook.notebookName" -}}
{{- printf "%s-notebook" (include "redis-notebook.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "redis-notebook.notebookLabels" -}}
{{ include "redis-notebook.labels" . }}
app.kubernetes.io/component: notebook
{{- end }}

{{- define "redis-notebook.notebookSelectorLabels" -}}
app.kubernetes.io/name: {{ include "redis-notebook.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: notebook
{{- end }}

{{- define "redis-notebook.roiDashboardName" -}}
{{- printf "%s-roi-dashboard" (include "redis-notebook.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "redis-notebook.roiDashboardLabels" -}}
{{ include "redis-notebook.labels" . }}
app.kubernetes.io/component: roi-dashboard
{{- end }}

{{- define "redis-notebook.roiDashboardSelectorLabels" -}}
app.kubernetes.io/name: {{ include "redis-notebook.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: roi-dashboard
{{- end }}

{{- define "redis-notebook.insuranceWorkerName" -}}
{{- printf "%s-insurance-worker" (include "redis-notebook.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "redis-notebook.insuranceWorkerLabels" -}}
{{ include "redis-notebook.labels" . }}
app.kubernetes.io/component: insurance-worker
{{- end }}

{{- define "redis-notebook.insuranceWorkerSelectorLabels" -}}
app.kubernetes.io/name: {{ include "redis-notebook.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: insurance-worker
{{- end }}

{{- define "redis-notebook.insuranceWorkerGitSyncRepo" -}}
{{- .Values.insuranceWorker.gitSync.repo | default .Values.roiDashboard.gitSync.repo -}}
{{- end }}

{{- define "redis-notebook.insuranceWorkerGitSyncBranch" -}}
{{- .Values.insuranceWorker.gitSync.branch | default .Values.roiDashboard.gitSync.branch -}}
{{- end }}

{{/*
Model + MaaS env vars shared by the Streamlit dashboard and RAK worker pods.
*/}}
{{- define "redis-notebook.modelEnv" -}}
- name: MODEL_API_KEY
  value: {{ .Values.secrets.model.apiKey | quote }}
- name: MODEL_ENDPOINT
  value: {{ .Values.secrets.model.endpoint | quote }}
- name: SIMPLE_MODEL_ENDPOINT
  value: {{ .Values.secrets.model.simpleEndpoint | default .Values.secrets.model.endpoint | default .Values.secrets.model.complexEndpoint | quote }}
- name: COMPLEX_MODEL_ENDPOINT
  value: {{ .Values.secrets.model.complexEndpoint | default .Values.secrets.model.endpoint | default .Values.secrets.model.simpleEndpoint | quote }}
- name: SIMPLE_MODEL_KEY
  value: {{ .Values.secrets.model.simpleApiKey | default .Values.secrets.model.apiKey | quote }}
- name: COMPLEX_MODEL_KEY
  value: {{ .Values.secrets.model.complexApiKey | default .Values.secrets.model.apiKey | quote }}
- name: COMPLEX_MODEL_NAME
  value: {{ .Values.secrets.model.complexModelName | quote }}
- name: SIMPLE_MODEL_NAME
  value: {{ .Values.secrets.model.simpleModelName | quote }}
{{- if or .Values.insuranceWorker.plainComplex .Values.roiDashboard.plainComplex }}
- name: INSURANCE_PLAIN_COMPLEX
  value: "true"
{{- end }}
- name: TOKENIZERS_PARALLELISM
  value: "false"
{{- end }}

{{/*
Wait for Redis Enterprise DB password Secret before worker/dashboard start.
*/}}
{{- define "redis-notebook.waitRedisEnterpriseSecretInitContainer" -}}
- name: wait-redis-db-secret
  image: registry.access.redhat.com/ubi9/ubi-minimal:latest
  imagePullPolicy: IfNotPresent
  command:
    - /bin/sh
    - -c
    - |
      set -eu
      echo "Waiting for Redis Enterprise DB secret {{ include "redis-notebook.redisEnterpriseSecretName" . }} (operator creates it when REDB is ready)..."
      i=0
      while [ "$i" -lt 720 ]; do
        if [ -f /redis-secret/password ] && [ -s /redis-secret/password ]; then
          echo "Secret is populated."
          exit 0
        fi
        i=$((i + 1))
        sleep 5
      done
      echo "Timed out after 1h. Check: oc get rec redb -n {{ .Release.Namespace }}; oc describe redb {{ .Values.redis.enterprise.database.name }} -n {{ .Release.Namespace }}"
      exit 1
  volumeMounts:
    - name: redis-enterprise-db-secret-wait
      mountPath: /redis-secret
      readOnly: true
{{- end }}

{{/*
Init container: clone demo/ for the RAK insurance worker (emptyDir workspace).
*/}}
{{- define "redis-notebook.insuranceWorkerGitSyncInitContainer" -}}
- name: git-sync-demo
  image: {{ .Values.insuranceWorker.gitSync.image | default .Values.roiDashboard.gitSync.image }}
  imagePullPolicy: IfNotPresent
  env:
    - name: GIT_SYNC_FORCE
      value: {{ if .Values.insuranceWorker.gitSync.forceRefresh }}"true"{{ else }}"false"{{ end }}
  command:
    - sh
    - -c
    - |
      set -e
      cd /workspace
      if [ "$GIT_SYNC_FORCE" != "true" ] && [ -f demo/shared/insurance_worker.py ]; then
        echo "demo/shared/insurance_worker.py already present; skipping git sync (set insuranceWorker.gitSync.forceRefresh=true to replace)."
        exit 0
      fi
      if [ "$GIT_SYNC_FORCE" = "true" ] && [ -d demo ]; then
        echo "Removing existing demo folder (forceRefresh)..."
        rm -rf demo
      fi
      echo "Cloning repository: {{ include "redis-notebook.insuranceWorkerGitSyncRepo" . }}"
      RETRIES=5
      COUNT=0
      until git clone --depth 1 {{ if include "redis-notebook.insuranceWorkerGitSyncBranch" . }}--branch {{ include "redis-notebook.insuranceWorkerGitSyncBranch" . }}{{ end }} {{ include "redis-notebook.insuranceWorkerGitSyncRepo" . }} /tmp/repo; do
        COUNT=$((COUNT+1))
        if [ $COUNT -ge $RETRIES ]; then
          echo "Failed to clone repository after $RETRIES attempts"
          exit 1
        fi
        echo "Clone failed, retrying in 10 seconds... (attempt $COUNT/$RETRIES)"
        sleep 10
      done
      echo "Copying demo folder to workspace..."
      if [ -d "/tmp/repo/demo" ]; then
        cp -rf /tmp/repo/demo . || { echo "Error: Failed to copy demo folder"; exit 1; }
        if [ ! -f "demo/shared/insurance_worker.py" ]; then
          echo "Error: demo/shared/insurance_worker.py missing after copy"
          exit 1
        fi
        echo "Demo folder successfully copied to workspace"
      else
        echo "Error: No demo directory found in repository"
        exit 1
      fi
      rm -rf /tmp/repo
      echo "Git sync completed successfully"
  volumeMounts:
    - name: workspace
      mountPath: /workspace
{{- end }}

{{- define "redis-notebook.redisUrl" -}}
{{- if .Values.redis.useRedisEnterpriseOperator }}
{{- $domain := .Values.global.clusterDomain | default "cluster.local" }}
{{- printf "redis://default:$(REDIS_PASSWORD)@%s.%s.svc.%s:$(REDIS_PORT)" .Values.redis.enterprise.database.name .Release.Namespace $domain }}
{{- else if .Values.redis.useOtContainerKitOperator }}
{{- $name := .Values.redisData.redisStandalone.name | default .Release.Name }}
{{- $domain := .Values.global.clusterDomain | default "cluster.local" }}
{{- printf "redis://%s.%s.svc.%s:6379" $name .Release.Namespace $domain }}
{{- else }}
{{- .Values.secrets.redis.url }}
{{- end }}
{{- end }}

{{/*
Redis Enterprise: name of the auto-generated DB password Secret.
Defaults to "redb-<database.name>" (the operator's v8.x naming convention) but
can be overridden via redis.enterprise.database.passwordSecretName.
*/}}
{{- define "redis-notebook.redisEnterpriseSecretName" -}}
{{- if .Values.redis.enterprise.database.passwordSecretName }}
{{- .Values.redis.enterprise.database.passwordSecretName }}
{{- else }}
{{- printf "redb-%s" .Values.redis.enterprise.database.name }}
{{- end }}
{{- end }}

{{/*
Notebook env entries for the chosen Redis backend. For OT-operator / external
paths this is just REDIS_URL. For Redis Enterprise we additionally inject
REDIS_PASSWORD + REDIS_PORT from the operator-managed secret and let Kubernetes
interpolate them into REDIS_URL with $(VAR) syntax.
*/}}
{{- define "redis-notebook.openshiftAIOperatorLabels" -}}
{{ include "redis-notebook.labels" . }}
app.kubernetes.io/component: openshift-ai-operator
{{- end }}

{{- define "redis-notebook.redisEnterpriseOLMLabels" -}}
{{ include "redis-notebook.labels" . }}
app.kubernetes.io/component: redis-enterprise-olm
{{- end }}

{{/*
Init container: clone notebook.gitSync.repo and copy demo/ into the workspace PVC.
Runs inside the notebook pod so ReadWriteOnce volumes are never shared with a separate Job.
*/}}
{{- define "redis-notebook.gitSyncInitContainer" -}}
- name: git-sync-demo
  image: {{ .Values.notebook.gitSync.image }}
  imagePullPolicy: IfNotPresent
  env:
    - name: GIT_SYNC_FORCE
      value: {{ if .Values.notebook.gitSync.forceRefresh }}"true"{{ else }}"false"{{ end }}
  command:
    - sh
    - -c
    - |
      set -e
      cd /opt/app-root/src
      if [ "$GIT_SYNC_FORCE" != "true" ] && [ -d demo/notebooks ]; then
        echo "demo/notebooks already present; skipping git sync (set notebook.gitSync.forceRefresh=true to replace)."
        exit 0
      fi
      if [ "$GIT_SYNC_FORCE" = "true" ] && [ -d demo ]; then
        echo "Removing existing demo folder (forceRefresh)..."
        rm -rf demo
      fi
      echo "Cloning repository: {{ .Values.notebook.gitSync.repo }}"
      RETRIES=5
      COUNT=0
      until git clone --depth 1 {{ if .Values.notebook.gitSync.branch }}--branch {{ .Values.notebook.gitSync.branch }}{{ end }} {{ .Values.notebook.gitSync.repo }} /tmp/repo; do
        COUNT=$((COUNT+1))
        if [ $COUNT -ge $RETRIES ]; then
          echo "Failed to clone repository after $RETRIES attempts"
          exit 1
        fi
        echo "Clone failed, retrying in 10 seconds... (attempt $COUNT/$RETRIES)"
        sleep 10
      done
      echo "Copying demo folder to workspace..."
      if [ -d "/tmp/repo/demo" ]; then
        cp -rf /tmp/repo/demo . || { echo "Error: Failed to copy demo folder"; exit 1; }
        if [ ! -d "demo/notebooks" ]; then
          echo "Error: demo/notebooks missing after copy"
          exit 1
        fi
        echo "Demo folder successfully copied to workspace"
      else
        echo "Error: No demo directory found in repository"
        exit 1
      fi
      rm -rf /tmp/repo
      echo "Git sync completed successfully"
  volumeMounts:
    - name: workspace
      mountPath: /opt/app-root/src
{{- end }}

{{/*
Init container: clone roiDashboard.gitSync.repo and copy demo/ into the workspace PVC.
Runs inside the roi-dashboard pod so ReadWriteOnce volumes are never shared with a separate Job.
*/}}
{{- define "redis-notebook.roiDashboardGitSyncInitContainer" -}}
- name: git-sync-demo
  image: {{ .Values.roiDashboard.gitSync.image }}
  imagePullPolicy: IfNotPresent
  env:
    - name: GIT_SYNC_FORCE
      value: {{ if .Values.roiDashboard.gitSync.forceRefresh }}"true"{{ else }}"false"{{ end }}
  command:
    - sh
    - -c
    - |
      set -e
      cd /workspace
      if [ "$GIT_SYNC_FORCE" != "true" ] && [ -f demo/app.py ]; then
        echo "demo/app.py already present; skipping git sync (set roiDashboard.gitSync.forceRefresh=true to replace)."
        exit 0
      fi
      if [ "$GIT_SYNC_FORCE" = "true" ] && [ -d demo ]; then
        echo "Removing existing demo folder (forceRefresh)..."
        rm -rf demo
      fi
      echo "Cloning repository: {{ .Values.roiDashboard.gitSync.repo }}"
      RETRIES=5
      COUNT=0
      until git clone --depth 1 {{ if .Values.roiDashboard.gitSync.branch }}--branch {{ .Values.roiDashboard.gitSync.branch }}{{ end }} {{ .Values.roiDashboard.gitSync.repo }} /tmp/repo; do
        COUNT=$((COUNT+1))
        if [ $COUNT -ge $RETRIES ]; then
          echo "Failed to clone repository after $RETRIES attempts"
          exit 1
        fi
        echo "Clone failed, retrying in 10 seconds... (attempt $COUNT/$RETRIES)"
        sleep 10
      done
      echo "Copying demo folder to workspace..."
      if [ -d "/tmp/repo/demo" ]; then
        cp -rf /tmp/repo/demo . || { echo "Error: Failed to copy demo folder"; exit 1; }
        if [ ! -f "demo/app.py" ]; then
          echo "Error: demo/app.py missing after copy"
          exit 1
        fi
        echo "Demo folder successfully copied to workspace"
      else
        echo "Error: No demo directory found in repository"
        exit 1
      fi
      rm -rf /tmp/repo
      echo "Git sync completed successfully"
  volumeMounts:
    - name: workspace
      mountPath: /workspace
{{- end }}

{{- define "redis-notebook.redisEnv" -}}
{{- if .Values.redis.useRedisEnterpriseOperator }}
- name: REDIS_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "redis-notebook.redisEnterpriseSecretName" . }}
      key: password
- name: REDIS_PORT
  valueFrom:
    secretKeyRef:
      name: {{ include "redis-notebook.redisEnterpriseSecretName" . }}
      key: port
- name: REDIS_URL
  value: {{ include "redis-notebook.redisUrl" . | quote }}
{{- else }}
- name: REDIS_URL
  value: {{ include "redis-notebook.redisUrl" . | quote }}
{{- end }}
{{- end }}
