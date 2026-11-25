variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "northamerica-northeast1"
}

variable "env" {
  type    = string
  default = "dev"
}

variable "prefix" {
  description = "Resource name prefix. The k8s manifests assume 'transit-lab'."
  type        = string
  default     = "transit-lab"
}

# --- Network -----------------------------------------------------------------
variable "subnet_cidr" {
  type    = string
  default = "10.10.0.0/20"
}

variable "pods_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "services_cidr" {
  type    = string
  default = "10.30.0.0/20"
}

variable "authorized_cidrs" {
  description = "CIDRs allowed on the control plane IP endpoint. Empty = DNS endpoint only (IAM)."
  type = list(object({
    cidr = string
    name = string
  }))
  default = []
}

# --- Edge security -----------------------------------------------------------
variable "rate_limit_per_minute" {
  description = "Requests per minute per IP before a 429 response."
  type        = number
  default     = 300
}

variable "allowed_countries" {
  description = "Allowed countries (geo rule in preview mode)."
  type        = list(string)
  default     = ["CA", "US"]
}

# --- Data (can be disabled to reduce costs) ----------------------------------
variable "enable_cloudsql" {
  type    = bool
  default = true
}

variable "enable_redis" {
  type    = bool
  default = true
}

variable "deletion_protection" {
  description = "Set to false before a terraform destroy."
  type        = bool
  default     = false
}
