output "argocd_access" {
  value = <<-EOT
    gcloud container clusters get-credentials ${local.infra.cluster_name} --region ${local.infra.cluster_location} --dns-endpoint
    kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
    kubectl -n argocd port-forward svc/argocd-server 8080:80
    # then http://localhost:8080  (user: admin)
  EOT
}

output "api_url" {
  value = "http://${local.infra.gateway_ip}/api/v1/vehicles"
}
