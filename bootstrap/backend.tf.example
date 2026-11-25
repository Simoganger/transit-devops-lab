# Rename to backend.tf AFTER the first bootstrap apply,
# then: terraform init -migrate-state -backend-config="bucket=<PROJECT_ID>-tfstate"
terraform {
  backend "gcs" {
    prefix = "bootstrap"
  }
}
