terraform {
  required_version = ">= 1.9.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.30"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.35"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 3.0"
    }
  }

  backend "gcs" {
    prefix = "platform"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Stack separate from "infra": the kubernetes/helm providers need an
# existing cluster at plan time. Separating them avoids the classic
# "provider configured with unknown values" problem.
data "terraform_remote_state" "infra" {
  backend = "gcs"
  config = {
    bucket = var.state_bucket
    prefix = "infra"
  }
}

data "google_client_config" "current" {}

data "google_container_cluster" "this" {
  name     = data.terraform_remote_state.infra.outputs.cluster_name
  location = data.terraform_remote_state.infra.outputs.cluster_location
}

locals {
  # DNS endpoint: Google public certificate, IAM token authentication.
  cluster_host = "https://${data.google_container_cluster.this.control_plane_endpoints_config[0].dns_endpoint_config[0].endpoint}"
}

provider "kubernetes" {
  host  = local.cluster_host
  token = data.google_client_config.current.access_token
}

provider "helm" {
  kubernetes = {
    host  = local.cluster_host
    token = data.google_client_config.current.access_token
  }
}
