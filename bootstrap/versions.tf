terraform {
  required_version = ">= 1.9.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.30"
    }
  }

  # First run: LOCAL state (the bucket does not exist yet).
  # Then: copy backend.tf.example -> backend.tf and run
  #   terraform init -migrate-state -backend-config="bucket=<PROJECT_ID>-tfstate"
}

provider "google" {
  project = var.project_id
  region  = var.region
}
