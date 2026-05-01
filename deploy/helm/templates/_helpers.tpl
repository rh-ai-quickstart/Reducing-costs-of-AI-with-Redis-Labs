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
- OT operator path: Redis CR service (name from redisData.redisStandalone.name or release name)
- Builtin path: in-chart Service (redis-notebook.redisBuiltinName)
- Else: secrets.redis.url (external)
*/}}
{{- define "redis-notebook.redisBuiltinName" -}}
{{- printf "%s-redis" (include "redis-notebook.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "redis-notebook.redisBuiltinLabels" -}}
{{ include "redis-notebook.labels" . }}
app.kubernetes.io/component: redis-builtin
{{- end }}

{{- define "redis-notebook.redisBuiltinSelectorLabels" -}}
app.kubernetes.io/name: {{ include "redis-notebook.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: redis-builtin
{{- end }}

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

{{- define "redis-notebook.redisConnectionConfigMapName" -}}
{{- if .Values.redis.connectionConfigMap.name }}
{{- .Values.redis.connectionConfigMap.name }}
{{- else }}
{{- printf "%s-redis-url" (include "redis-notebook.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "redis-notebook.redisUrl" -}}
{{- if .Values.redis.useRedisEnterpriseOperator }}
{{- $domain := .Values.global.clusterDomain | default "cluster.local" }}
{{- printf "redis://default:$(REDIS_PASSWORD)@%s.%s.svc.%s:$(REDIS_PORT)" .Values.redis.enterprise.database.name .Release.Namespace $domain }}
{{- else if .Values.redis.useOtContainerKitOperator }}
{{- $name := .Values.redisData.redisStandalone.name | default .Release.Name }}
{{- $domain := .Values.global.clusterDomain | default "cluster.local" }}
{{- printf "redis://%s.%s.svc.%s:6379" $name .Release.Namespace $domain }}
{{- else if .Values.redis.builtin.enabled }}
{{- $domain := .Values.global.clusterDomain | default "cluster.local" }}
{{- printf "redis://%s.%s.svc.%s:%v" (include "redis-notebook.redisBuiltinName" .) .Release.Namespace $domain .Values.redis.builtin.service.port }}
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
Notebook env entries for the chosen Redis backend. For builtin / OT-operator /
external paths this is just REDIS_URL. For Redis Enterprise we additionally
inject REDIS_PASSWORD + REDIS_PORT from the operator-managed secret and let
Kubernetes interpolate them into REDIS_URL with $(VAR) syntax.
*/}}
{{- define "redis-notebook.openshiftAIOperatorLabels" -}}
{{ include "redis-notebook.labels" . }}
app.kubernetes.io/component: openshift-ai-operator
{{- end }}

{{- define "redis-notebook.redisEnterpriseOLMLabels" -}}
{{ include "redis-notebook.labels" . }}
app.kubernetes.io/component: redis-enterprise-olm
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
