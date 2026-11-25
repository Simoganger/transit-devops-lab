output "cluster_name" {
  value = google_container_cluster.autopilot.name
}

output "cluster_location" {
  value = google_container_cluster.autopilot.location
}

output "artifact_repo_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.transit.repository_id}"
}

output "gateway_ip_name" {
  value = google_compute_global_address.gateway.name
}

output "gateway_ip" {
  value = google_compute_global_address.gateway.address
}

output "security_policy_name" {
  value = google_compute_security_policy.edge.name
}

output "pubsub_topic" {
  value = google_pubsub_topic.vehicle_positions.name
}

output "redis_host" {
  value = var.enable_redis ? google_redis_instance.cache[0].host : ""
}

output "redis_port" {
  value = var.enable_redis ? google_redis_instance.cache[0].port : 0
}

output "db_private_ip" {
  value = var.enable_cloudsql ? google_sql_database_instance.postgres[0].private_ip_address : ""
}

output "db_connection_name" {
  value = var.enable_cloudsql ? google_sql_database_instance.postgres[0].connection_name : ""
}

output "db_secret_id" {
  value = var.enable_cloudsql ? google_secret_manager_secret.db_password[0].secret_id : ""
}
