resource "google_secret_manager_secret" "mp_secrets" {
  for_each = toset(var.mp_secret_names)

  project   = var.project_id
  secret_id = each.value

  replication {
    auto {}
  }

  labels = {
    env = "prod"
  }

  depends_on = [google_project_service.enabled]
}

# Versión placeholder: reemplazar manualmente con el valor real, por ejemplo:
#   echo -n "VALOR_REAL" | gcloud secrets versions add <secret_id> --data-file=- --project=<project_id>
# Terraform no vuelve a tocar el valor una vez aplicado (lifecycle.ignore_changes).
resource "google_secret_manager_secret_version" "mp_secret_placeholder" {
  for_each = google_secret_manager_secret.mp_secrets

  secret      = each.value.id
  secret_data = "REEMPLAZAR_VALOR_REAL"

  lifecycle {
    ignore_changes = [secret_data]
  }
}
