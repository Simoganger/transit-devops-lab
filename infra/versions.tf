terraform {
  required_version = ">= 1.9.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.30"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Bucket passed at init: terraform init -backend-config="bucket=<PROJECT_ID>-tfstate"
  # Locking is native with the GCS backend (.tflock file).
  backend "gcs" {
    prefix = "infra"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region

  default_labels = {
    env        = var.env
    managed-by = "terraform"
    lab        = "transit-devops"
  }
}
