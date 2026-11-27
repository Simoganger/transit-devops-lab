# project_id is supplied by TF_VAR_project_id (CI) or -var locally.
env                   = "dev"
region                = "northamerica-northeast1"
prefix                = "transit-lab"
rate_limit_per_minute = 300
allowed_countries     = ["CA", "US"]
enable_cloudsql       = false
enable_redis          = false
deletion_protection   = false

# Optional: allow your IP on the control plane IP endpoint.
# authorized_cidrs = [{ cidr = "203.0.113.10/32", name = "home" }]
