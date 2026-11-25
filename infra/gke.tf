###############################################################################
# GKE AUTOPILOT
#  - Private nodes (no public IP), egress through Cloud NAT
#  - Control plane reachable through the DNS endpoint (IAM authentication),
#    which lets GitHub Actions reach it without an IP allowlist
#  - Gateway API enabled (global L7 load balancer + Cloud Armor)
#  - Dedicated, least-privilege node service account
###############################################################################

resource "google_service_account" "gke_nodes" {
  account_id   = "${var.prefix}-gke-nodes"
  display_name = "GKE Autopilot nodes (${var.env})"
}

resource "google_project_iam_member" "gke_nodes" {
  for_each = toset([
    "roles/container.defaultNodeServiceAccount",
    "roles/artifactregistry.reader",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

resource "google_container_cluster" "autopilot" {
  name     = "${var.prefix}-gke"
  location = var.region

  enable_autopilot    = true
  deletion_protection = var.deletion_protection

  network    = google_compute_network.vpc.id
  subnetwork = google_compute_subnetwork.gke.id

  release_channel {
    channel = "REGULAR"
  }

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
  }

  # IP endpoint: closed by default (no authorized CIDR).
  master_authorized_networks_config {
    gcp_public_cidrs_access_enabled = false

    dynamic "cidr_blocks" {
      for_each = var.authorized_cidrs
      content {
        cidr_block   = cidr_blocks.value.cidr
        display_name = cidr_blocks.value.name
      }
    }
  }

  # DNS endpoint: IAM-authenticated access from anywhere.
  control_plane_endpoints_config {
    dns_endpoint_config {
      allow_external_traffic = true
    }
  }

  gateway_api_config {
    channel = "CHANNEL_STANDARD"
  }

  cluster_autoscaling {
    auto_provisioning_defaults {
      service_account = google_service_account.gke_nodes.email
      oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]
    }
  }

  maintenance_policy {
    recurring_window {
      # Off-peak window (UTC): Sun 07:00-11:00 UTC = 02:00-06:00 in Montreal.
      start_time = "2025-01-05T07:00:00Z"
      end_time   = "2025-01-05T11:00:00Z"
      recurrence = "FREQ=WEEKLY;BYDAY=SU"
    }
  }

  depends_on = [google_project_iam_member.gke_nodes]
}
