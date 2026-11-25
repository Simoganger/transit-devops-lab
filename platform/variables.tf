variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "northamerica-northeast1"
}

variable "state_bucket" {
  description = "Terraform state bucket (to read the infra stack outputs)."
  type        = string
}

variable "gitops_repo_url" {
  description = "HTTPS URL of the GitOps repository watched by ArgoCD."
  type        = string
}

variable "gitops_revision" {
  type    = string
  default = "main"
}

variable "argocd_chart_version" {
  description = "argo/argo-cd chart version. null = latest. In production: ALWAYS pin (helm search repo argo/argo-cd)."
  type        = string
  default     = null
}

variable "argocd_apps_chart_version" {
  description = "argo/argocd-apps chart version (>= 2.0, map format). null = latest."
  type        = string
  default     = null
}
