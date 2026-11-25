###############################################################################
# DATA SERVICES for the "real-time vehicle positions" use case
#  - Pub/Sub: event-driven ingestion of positions (GTFS-Realtime style)
#             with a dead-letter topic
#  - Memorystore Redis: cache of the positions snapshot (short TTL)
#  - Cloud SQL PostgreSQL: reference data (routes, stops) - private IP only
#  - Secret Manager: database password
###############################################################################

data "google_project" "this" {
  project_id = var.project_id
}

# --- Pub/Sub -----------------------------------------------------------------
resource "google_pubsub_topic" "vehicle_positions" {
  name                       = "vehicle-positions"
  message_retention_duration = "86400s"
}

resource "google_pubsub_topic" "vehicle_positions_dlq" {
  name = "vehicle-positions-dlq"
}

resource "google_pubsub_subscription" "vehicle_positions_processor" {
  name                       = "vehicle-positions-processor"
  topic                      = google_pubsub_topic.vehicle_positions.id
  ack_deadline_seconds       = 20
  message_retention_duration = "3600s"
  enable_message_ordering    = true # ordering guaranteed per key (e.g. vehicle_id)

  retry_policy {
    minimum_backoff = "5s"
    maximum_backoff = "60s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.vehicle_positions_dlq.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_subscription" "vehicle_positions_dlq_inspect" {
  name                       = "vehicle-positions-dlq-inspect"
  topic                      = google_pubsub_topic.vehicle_positions_dlq.id
  message_retention_duration = "604800s"
}

# The Pub/Sub service agent must be able to publish to the DLQ and
# acknowledge messages on the source subscription.
locals {
  pubsub_agent = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_topic_iam_member" "dlq_publisher" {
  topic  = google_pubsub_topic.vehicle_positions_dlq.id
  role   = "roles/pubsub.publisher"
  member = local.pubsub_agent
}

resource "google_pubsub_subscription_iam_member" "dlq_subscriber" {
  subscription = google_pubsub_subscription.vehicle_positions_processor.id
  role         = "roles/pubsub.subscriber"
  member       = local.pubsub_agent
}

# --- Memorystore Redis ------------------------------------------------------------
resource "google_redis_instance" "cache" {
  count = var.enable_redis ? 1 : 0

  name               = "${var.prefix}-cache"
  tier               = "BASIC" # STANDARD_HA in production (replica + failover)
  memory_size_gb     = 1
  region             = var.region
  redis_version      = "REDIS_7_2"
  authorized_network = google_compute_network.vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  depends_on = [google_service_networking_connection.psa]
}

# --- Cloud SQL PostgreSQL -----------------------------------------------------------
resource "random_password" "db" {
  count   = var.enable_cloudsql ? 1 : 0
  length  = 32
  special = false
}

resource "google_sql_database_instance" "postgres" {
  count = var.enable_cloudsql ? 1 : 0

  name                = "${var.prefix}-pg"
  region              = var.region
  database_version    = "POSTGRES_16"
  deletion_protection = var.deletion_protection

  settings {
    tier              = "db-f1-micro" # production: db-custom-2-8192 + REGIONAL
    edition           = "ENTERPRISE"
    availability_type = "ZONAL"
    disk_autoresize   = true

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
      ssl_mode        = "ENCRYPTED_ONLY"
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "07:00"
      backup_retention_settings {
        retained_backups = 7
      }
    }

    insights_config {
      query_insights_enabled = true
    }

    database_flags {
      name  = "log_min_duration_statement"
      value = "500"
    }
  }

  depends_on = [google_service_networking_connection.psa]
}

resource "google_sql_database" "transit" {
  count    = var.enable_cloudsql ? 1 : 0
  name     = "transit"
  instance = google_sql_database_instance.postgres[0].name
}

resource "google_sql_user" "app" {
  count    = var.enable_cloudsql ? 1 : 0
  name     = "app"
  instance = google_sql_database_instance.postgres[0].name
  password = random_password.db[0].result
}

# --- Secret Manager ---------------------------------------------------------
resource "google_secret_manager_secret" "db_password" {
  count     = var.enable_cloudsql ? 1 : 0
  secret_id = "${var.prefix}-db-password"

  replication {
    user_managed {
      replicas {
        location = var.region # data residency in Canada
      }
    }
  }
}

resource "google_secret_manager_secret_version" "db_password" {
  count       = var.enable_cloudsql ? 1 : 0
  secret      = google_secret_manager_secret.db_password[0].id
  secret_data = random_password.db[0].result
}
