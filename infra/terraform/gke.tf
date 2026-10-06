resource "google_container_cluster" "primary" {
  provider = google-beta
  project  = var.project_id
  name     = "postnetmp-zonal"
  location = var.zone # clúster zonal: sin costo de gestión (1 clúster zonal gratis por cuenta de billing)

  remove_default_node_pool = true
  initial_node_count       = 1
  networking_mode          = "VPC_NATIVE"
  deletion_protection      = false

  ip_allocation_policy {}

  release_channel {
    channel = "REGULAR"
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  addons_config {
    horizontal_pod_autoscaling {
      disabled = false
    }
    http_load_balancing {
      disabled = true # sin Ingress/LB administrado: evita costo de forwarding rule
    }
  }

  depends_on = [google_project_service.enabled]
}

resource "google_container_node_pool" "free_tier_pool" {
  project  = var.project_id
  name     = "free-tier-pool"
  cluster  = google_container_cluster.primary.name
  location = var.zone

  # Nodo único e2-micro: elegible para el Always Free Tier de Compute Engine en
  # us-west1 / us-central1 / us-east1. Sin autoscaling, para que el escalado
  # nunca pueda generar costo fuera de la capa gratuita.
  node_count = 1

  node_config {
    machine_type = "e2-micro"
    disk_size_gb = 30
    disk_type    = "pd-standard"
    preemptible  = false
    spot         = false

    service_account = google_service_account.gke_node_sa.email
    oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]

    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    labels = {
      tier = "free"
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  # Sin bloque "autoscaling": tamaño fijo en 1 nodo (techo duro de cómputo).
}
