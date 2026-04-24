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

{{- define "redis-notebook.redisConnectionConfigMapName" -}}
{{- if .Values.redis.connectionConfigMap.name }}
{{- .Values.redis.connectionConfigMap.name }}
{{- else }}
{{- printf "%s-redis-url" (include "redis-notebook.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "redis-notebook.redisUrl" -}}
{{- if .Values.redis.useOtContainerKitOperator }}
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
