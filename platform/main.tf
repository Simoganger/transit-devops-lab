###############################################################################
# PLATFORM: what lives INSIDE the cluster and belongs to the platform team.
#  - "transit" namespace + ConfigMap populated from the infra outputs
#    (bridge between Terraform and GitOps: no hard-coded values in Git)
#  - ArgoCD (Helm)
#  - ArgoCD Application that syncs k8s/overlays/dev from Git
###############################################################################

locals {
  infra = data.terraform_remote_state.infra.outputs
}

resource "kubernetes_namespace" "transit" {
  metadata {
    name = "transit"
    labels = {
      "app.kubernetes.io/part-of"          = "mobility"
      "pod-security.kubernetes.io/enforce" = "restricted"
    }
  }
}

resource "kubernetes_config_map" "transit_config" {
  metadata {
    name      = "transit-config"
    namespace = kubernetes_namespace.transit.metadata[0].name
  }

  data = {
    GCP_PROJECT_ID = var.project_id
    PUBSUB_TOPIC   = local.infra.pubsub_topic
    REDIS_HOST     = local.infra.redis_host
    REDIS_PORT     = tostring(local.infra.redis_port)
    DB_HOST        = local.infra.db_private_ip
    DB_NAME        = "transit"
    DB_SECRET_ID   = local.infra.db_secret_id
  }
}

resource "helm_release" "argocd" {
  name             = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = var.argocd_chart_version
  namespace        = "argocd"
  create_namespace = true
  timeout          = 900

  values = [yamlencode({
    global = {
      domain = "argocd.local"
    }
    configs = {
      params = {
        # TLS terminated elsewhere; access through port-forward in this lab.
        "server.insecure" = true
      }
      cm = {
        "timeout.reconciliation" = "60s"
      }
    }
    dex = {
      enabled = false # in production: OIDC SSO (Entra ID / Google Workspace)
    }
    server = {
      service = { type = "ClusterIP" }
    }
    controller = {
      resources = {
        requests = { cpu = "250m", memory = "512Mi" }
      }
    }
  })]
}

resource "helm_release" "argocd_apps" {
  name       = "argocd-apps"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argocd-apps"
  version    = var.argocd_apps_chart_version
  namespace  = "argocd"

  values = [yamlencode({
    applications = {
      vehicle-api = {
        namespace = "argocd"
        project   = "default"
        source = {
          repoURL        = var.gitops_repo_url
          targetRevision = var.gitops_revision
          path           = "k8s/overlays/dev"
        }
        destination = {
          server    = "https://kubernetes.default.svc"
          namespace = "transit"
        }
        syncPolicy = {
          automated = {
            prune    = true # deletes whatever was removed from Git
            selfHeal = true # reverts manual changes (drift)
          }
          syncOptions = ["ServerSideApply=true"]
          retry = {
            limit   = 5
            backoff = { duration = "10s", factor = 2, maxDuration = "3m" }
          }
        }
      }
    }
  })]

  depends_on = [helm_release.argocd, kubernetes_config_map.transit_config]
}
