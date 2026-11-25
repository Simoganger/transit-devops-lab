###############################################################################
# Minimal OBSERVABILITY: alert when the DLQ receives messages
# (a sign that position processing is failing).
# Add a notification channel (email, PagerDuty) via notification_channels.
###############################################################################

resource "google_monitoring_alert_policy" "dlq_not_empty" {
  display_name = "[${var.env}] Dead-lettered messages (vehicle-positions)"
  combiner     = "OR"

  conditions {
    display_name = "DLQ contains unacknowledged messages"
    condition_threshold {
      filter          = "resource.type = \"pubsub_subscription\" AND resource.labels.subscription_id = \"${google_pubsub_subscription.vehicle_positions_dlq_inspect.name}\" AND metric.type = \"pubsub.googleapis.com/subscription/num_undelivered_messages\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "300s"

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MAX"
      }
    }
  }

  documentation {
    content   = "Some vehicle positions could not be processed after 5 attempts. Runbook: inspect vehicle-positions-dlq-inspect, fix, replay."
    mime_type = "text/markdown"
  }
}
