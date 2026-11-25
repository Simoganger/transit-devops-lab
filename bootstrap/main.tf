###############################################################################
# BOOTSTRAP: everything that must exist BEFORE CI can do its work.
#  1. Project APIs
#  2. GCS bucket for the Terraform state files (versioned, private)
#  3. Workload Identity Federation GitHub -> GCP (no JSON key)
#  4. Service accounts: gh-terraform (IaC) and gh-ci (image push)
###############################################################################

locals {
  apis = [
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
    "compute.googleapis.com",
    "container.googleapis.com",
    "artifactregistry.googleapis.com",
    "sqladmin.googleapis.com",
    "servicenetworking.googleapis.com",
    "redis.googleapis.com",
    "pubsub.googleapis.com",
    "secretmanager.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "dns.googleapis.com",
  ]

  # Roles for the Terraform account. Deliberately narrower than roles/owner.
  # In production: one SA per stack (network, GKE, data) and custom roles.
  terraform_roles = [
    "roles/compute.admin",
    "roles/container.admin",
    "roles/artifactregistry.admin",
    "roles/cloudsql.admin",
    "roles/redis.admin",
    "roles/pubsub.admin",
    "roles/secretmanager.admin",
    "roles/servicenetworking.networksAdmin",
    "roles/iam.serviceAccountAdmin",
    "roles/iam.serviceAccountUser",
    "roles/resourcemanager.projectIamAdmin",
    "roles/serviceusage.serviceUsageConsumer",
    "roles/monitoring.admin",
    "roles/dns.admin",
  ]
}

data "google_project" "this" {
  project_id = var.project_id
}

# --- 1. APIs -----------------------------------------------------------------
resource "google_project_service" "apis" {
  for_each = toset(local.apis)

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# --- 2. Terraform state bucket ----------------------------------------------
resource "google_storage_bucket" "tfstate" {
  name     = "${var.project_id}-tfstate"
  project  = var.project_id
  location = var.region

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  # Versioning makes it possible to restore a corrupted or overwritten state.
  versioning {
    enabled = true
  }

  # Keep the last 10 noncurrent versions, for at most 90 days.
  lifecycle_rule {
    condition {
      num_newer_versions = 10
      with_state         = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      days_since_noncurrent_time = 90
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    usage = "terraform-state"
  }
}

# --- 3. Workload Identity Federation (GitHub OIDC) ---------------------------
resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  description               = "Identity federation for GitHub Actions (keyless)."

  depends_on = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
    "attribute.ref"              = "assertion.ref"
  }

  # Only THIS repository can obtain a token. Essential: without a condition,
  # any GitHub repository could present itself.
  attribute_condition = "assertion.repository == '${var.github_repo}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# --- 4. Service accounts -----------------------------------------------------
resource "google_service_account" "terraform" {
  project      = var.project_id
  account_id   = "gh-terraform"
  display_name = "GitHub Actions - Terraform"
}

resource "google_service_account" "ci" {
  project      = var.project_id
  account_id   = "gh-ci"
  display_name = "GitHub Actions - image build and push"
}

resource "google_project_iam_member" "terraform_roles" {
  for_each = toset(local.terraform_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.terraform.email}"
}

# State access limited to the bucket (not the whole project).
resource "google_storage_bucket_iam_member" "terraform_state" {
  bucket = google_storage_bucket.tfstate.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.terraform.email}"
}

resource "google_project_iam_member" "ci_ar_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.ci.email}"
}

# The GitHub repository can "become" these service accounts.
resource "google_service_account_iam_member" "terraform_wif" {
  service_account_id = google_service_account.terraform.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}

resource "google_service_account_iam_member" "ci_wif" {
  service_account_id = google_service_account.ci.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}
