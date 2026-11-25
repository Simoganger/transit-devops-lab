###############################################################################
# WORKLOAD IDENTITY (GKE): the Kubernetes ServiceAccount transit/vehicle-api
# is granted IAM roles directly, with no intermediate Google service account
# and no JSON key (Workload Identity "principal" binding).
###############################################################################

locals {
  k8s_namespace = "transit"
  k8s_sa        = "vehicle-api"

  vehicle_api_principal = "principal://iam.googleapis.com/projects/${data.google_project.this.number}/locations/global/workloadIdentityPools/${var.project_id}.svc.id.goog/subject/ns/${local.k8s_namespace}/sa/${local.k8s_sa}"
}

resource "google_pubsub_topic_iam_member" "vehicle_api_publisher" {
  topic  = google_pubsub_topic.vehicle_positions.id
  role   = "roles/pubsub.publisher"
  member = local.vehicle_api_principal

  depends_on = [google_container_cluster.autopilot] # the *.svc.id.goog pool must exist
}

resource "google_secret_manager_secret_iam_member" "vehicle_api_db_secret" {
  count     = var.enable_cloudsql ? 1 : 0
  secret_id = google_secret_manager_secret.db_password[0].id
  role      = "roles/secretmanager.secretAccessor"
  member    = local.vehicle_api_principal

  depends_on = [google_container_cluster.autopilot]
}

resource "google_project_iam_member" "vehicle_api_sql_client" {
  count   = var.enable_cloudsql ? 1 : 0
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = local.vehicle_api_principal

  depends_on = [google_container_cluster.autopilot]
}
