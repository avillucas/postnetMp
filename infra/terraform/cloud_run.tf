resource "google_cloud_run_v2_service" "payment_api" {
  project  = var.project_id
  name     = "payment-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.cloud_run_sa.email

    scaling {
      min_instance_count = 0 # escala a cero: sin costo en reposo
      max_instance_count = 2 # techo duro para no exceder cuota gratuita de solicitudes/cómputo
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}/payment-api:latest"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true # CPU asignada solo durante el procesamiento de requests
      }

      dynamic "env" {
        for_each = var.mp_secret_names
        content {
          name = upper(replace(env.value, "-", "_"))
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.enabled,
    google_secret_manager_secret_version.mp_secret_placeholder,
  ]

  lifecycle {
    # La imagen real se publica vía Cloud Build; Terraform no debe revertir
    # el despliegue hecho por el pipeline.
    ignore_changes = [template]
  }
}

# Acceso público al endpoint de pagos. Restringir a "roles/run.invoker" sobre
# una identidad concreta si se requiere autenticación (p. ej. el simulador).
resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  project  = google_cloud_run_v2_service.payment_api.project
  location = google_cloud_run_v2_service.payment_api.location
  name     = google_cloud_run_v2_service.payment_api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
