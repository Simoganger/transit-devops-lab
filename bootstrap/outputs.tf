output "tf_state_bucket" {
  description = "GCS bucket for the Terraform state."
  value       = google_storage_bucket.tfstate.name
}

output "wif_provider" {
  description = "Full name of the WIF provider, to put in the GitHub variable GCP_WIF_PROVIDER."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "terraform_sa" {
  value = google_service_account.terraform.email
}

output "ci_sa" {
  value = google_service_account.ci.email
}

output "github_variables_commands" {
  description = "gh commands to run to configure the repository."
  value       = <<-EOT
    gh variable set GCP_PROJECT_ID   --body "${var.project_id}"
    gh variable set GCP_REGION       --body "${var.region}"
    gh variable set TF_STATE_BUCKET  --body "${google_storage_bucket.tfstate.name}"
    gh variable set GCP_WIF_PROVIDER --body "${google_iam_workload_identity_pool_provider.github.name}"
    gh variable set GCP_TF_SA        --body "${google_service_account.terraform.email}"
    gh variable set GCP_CI_SA        --body "${google_service_account.ci.email}"
  EOT
}
