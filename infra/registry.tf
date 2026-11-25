resource "google_artifact_registry_repository" "transit" {
  location      = var.region
  repository_id = "transit"
  description   = "Mobility service images"
  format        = "DOCKER"

  docker_config {
    immutable_tags = true # a published tag can never be overwritten
  }

  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "keep-10-recent"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-older-30d"
    action = "DELETE"
    condition {
      tag_state  = "ANY"
      older_than = "2592000s"
    }
  }
}
