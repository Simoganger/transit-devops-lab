###############################################################################
# CLOUD ARMOR: WAF + L7 anti-DDoS + rate limiting, attached to the GKE
# Gateway backend by the GCPBackendPolicy resource (see k8s/base/gateway.yaml).
#
# Evaluation order: lowest priority first.
#   100       : allowlist (e.g. monitoring IPs) - optional
#   1000-1050 : preconfigured OWASP WAF rules
#   2000      : per-IP rate limiting (429)
#   3000      : geo-filtering in PREVIEW mode (logged, not blocking)
#   default   : allow
###############################################################################

resource "google_compute_security_policy" "edge" {
  name        = "${var.prefix}-edge-policy"
  description = "WAF, rate limiting and DDoS protection for the transit API"
  type        = "CLOUD_ARMOR"

  adaptive_protection_config {
    layer_7_ddos_defense_config {
      enable = true
    }
  }

  advanced_options_config {
    log_level    = "VERBOSE"
    json_parsing = "STANDARD"
  }

  # --- OWASP WAF (sensitivity 1 = fewer false positives) ----------------------
  rule {
    action      = "deny(403)"
    priority    = 1000
    description = "OWASP - SQL injection"
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('sqli-v33-stable', {'sensitivity': 1})"
      }
    }
  }

  rule {
    action      = "deny(403)"
    priority    = 1010
    description = "OWASP - XSS"
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('xss-v33-stable', {'sensitivity': 1})"
      }
    }
  }

  rule {
    action      = "deny(403)"
    priority    = 1020
    description = "OWASP - local file inclusion"
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('lfi-v33-stable', {'sensitivity': 1})"
      }
    }
  }

  rule {
    action      = "deny(403)"
    priority    = 1030
    description = "OWASP - remote code execution"
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('rce-v33-stable', {'sensitivity': 1})"
      }
    }
  }

  rule {
    action      = "deny(403)"
    priority    = 1040
    description = "Scanner detection"
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('scannerdetection-v33-stable', {'sensitivity': 1})"
      }
    }
  }

  # --- Per-IP rate limiting -----------------------------------------------------
  rule {
    action      = "throttle"
    priority    = 2000
    description = "Max ${var.rate_limit_per_minute} req/min per IP"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = var.rate_limit_per_minute
        interval_sec = 60
      }
    }
  }

  # --- Geo-filtering in preview: measure before blocking ---------------------
  rule {
    action      = "deny(403)"
    priority    = 3000
    description = "Outside allowed countries (PREVIEW)"
    preview     = true
    match {
      expr {
        expression = join(" && ", [for c in var.allowed_countries : "origin.region_code != '${c}'"])
      }
    }
  }

  # --- Default rule -----------------------------------------------------------------
  rule {
    action      = "allow"
    priority    = 2147483647
    description = "Default"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
  }
}
