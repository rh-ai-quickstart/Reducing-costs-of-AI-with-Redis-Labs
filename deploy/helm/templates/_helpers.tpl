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
Redis connection URL for notebooks: in-cluster OT operator Redis, or secrets.redis.url when redis.enabled is false.
Service host matches the Redis CR name (redisData.redisStandalone.name, defaulting to the Helm release name).
*/}}
{{- define "redis-notebook.redisUrl" -}}
{{- if .Values.redis.enabled }}
{{- $name := .Values.redisData.redisStandalone.name | default .Release.Name }}
{{- $domain := .Values.global.clusterDomain | default "cluster.local" }}
{{- printf "redis://%s.%s.svc.%s:6379" $name .Release.Namespace $domain }}
{{- else }}
{{- .Values.secrets.redis.url }}
{{- end }}
{{- end }}
