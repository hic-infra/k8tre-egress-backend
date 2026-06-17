{{/*
Expand the name of the chart.
*/}}
{{- define "hic-egress-backend.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "hic-egress-backend.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- printf "%s" $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "hic-egress-backend.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{ include "hic-egress-backend.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels - used by both Deployment's pod template and Service's selector.
Keeping this in one place is what guarantees they never drift apart.
*/}}
{{- define "hic-egress-backend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "hic-egress-backend.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
