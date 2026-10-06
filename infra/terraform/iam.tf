resource "google_service_account" "cloud_run_sa" {
  project      = var.project_id
  account_id   = "payment-api-run-sa"
  display_name = "Cloud Run - FastAPI Payment API"
}

resource "google_service_account" "gke_node_sa" {
  project      = var.project_id
  account_id   = "gke-celery-node-sa"
  display_name = "Nodo GKE - Celery/Redis (permisos mínimos)"
}

resource "google_service_account" "celery_worker_gsa" {
  project      = var.project_id
  account_id   = "celery-worker-gsa"
  display_name = "Workload Identity - Celery worker"
}

resource "google_service_account" "cloudbuild_sa" {
  project      = var.project_id
  account_id   = "cicd-deployer-sa"
  display_name = "Cloud Build - CI/CD deployer"
}

# Permisos mínimos del nodo GKE: solo logging/monitoring y lectura de imágenes.
resource "google_project_iam_member" "gke_node_roles" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer",
    "roles/artifactregistry.reader",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.gke_node_sa.email}"
}

# Cloud Run SA: acceso de lectura solo a los secretos que consume.
resource "google_secret_manager_secret_iam_member" "cloud_run_secret_access" {
  for_each = google_secret_manager_secret.mp_secrets

  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Workload Identity: la KSA "celery-worker-sa" (namespace "expendedora") suplanta a esta GSA.
resource "google_service_account_iam_member" "celery_workload_identity" {
  service_account_id = google_service_account.celery_worker_gsa.name
  role                = "roles/iam.workloadIdentityUser"
  member              = "serviceAccount:${var.project_id}.svc.id.goog[expendedora/celery-worker-sa]"
}

resource "google_secret_manager_secret_iam_member" "celery_secret_access" {
  for_each = google_secret_manager_secret.mp_secrets

  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.celery_worker_gsa.email}"
}

# Cloud Build: permisos acotados para build + deploy, sin roles de Owner/Editor.
resource "google_project_iam_member" "cloudbuild_roles" {
  for_each = toset([
    "roles/run.admin",
    "roles/container.developer",
    "roles/artifactregistry.writer",
    "roles/iam.serviceAccountUser",
    "roles/logging.logWriter",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cloudbuild_sa.email}"
}
