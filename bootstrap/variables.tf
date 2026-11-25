variable "project_id" {
  description = "ID of the lab's GCP project."
  type        = string
}

variable "region" {
  description = "GCP region (Montreal by default: data residency in Canada)."
  type        = string
  default     = "northamerica-northeast1"
}

variable "github_repo" {
  description = "GitHub repository allowed to authenticate through OIDC, in owner/repo format."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repo))
    error_message = "Expected format: owner/repo."
  }
}
