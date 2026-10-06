output "cloud_run_url" {
  description = "URL pública de la API de pagos en Cloud Run."
  value       = google_cloud_run_v2_service.payment_api.uri
}

output "gke_cluster_name" {
  description = "Nombre del clúster GKE zonal."
  value       = google_container_cluster.primary.name
}

output "artifact_registry_repo" {
  description = "Repositorio de Artifact Registry para las imágenes Docker."
  value       = google_artifact_registry_repository.images.name
}

output "cloudbuild_sa_email" {
  description = "Service account usada por el trigger de Cloud Build."
  value       = google_service_account.cloudbuild_sa.email
}

output "celery_worker_gsa_email" {
  description = "Service account de GCP enlazada vía Workload Identity al pod de Celery."
  value       = google_service_account.celery_worker_gsa.email
}
