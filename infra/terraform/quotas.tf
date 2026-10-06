# Techo duro de cómputo a nivel de proyecto: evita que Compute Engine/GKE
# escale por encima de lo bonificado por el Always Free Tier.
#
# NOTA: la reducción de cuotas vía Terraform/API puede requerir permisos de
# "Quota Administrator" y no siempre se aplica igual en todas las métricas.
# Verificar el resultado en Console > IAM y administración > Cuotas y, si el
# override no se aplica, reducir la cuota manualmente desde ahí.
resource "google_service_usage_consumer_quota_override" "compute_cpus_all_regions" {
  provider       = google-beta
  project        = var.project_id
  service        = "compute.googleapis.com"
  metric         = urlencode("compute.googleapis.com/cpus")
  limit          = urlencode("/project/region")
  override_value = tostring(var.compute_cpu_quota_cap)
  force          = true

  depends_on = [google_project_service.enabled]
}
