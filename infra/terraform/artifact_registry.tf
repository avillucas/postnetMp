resource "google_artifact_registry_repository" "images" {
  project       = var.project_id
  location      = var.region
  repository_id = "postnetmp-images"
  description   = "Imágenes Docker de la API de pagos (FastAPI) y los workers Celery."
  format        = "DOCKER"

  # Limita versiones guardadas para no acumular almacenamiento innecesario.
  cleanup_policies {
    id     = "keep-last-5"
    action = "KEEP"
    most_recent_versions {
      keep_count = 5
    }
  }

  depends_on = [google_project_service.enabled]
}
