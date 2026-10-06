variable "project_id" {
  description = "ID del proyecto de GCP donde se despliega la arquitectura."
  type        = string
}

variable "billing_account_id" {
  description = "ID de la cuenta de Billing a vincular con el proyecto (formato XXXXXX-XXXXXX-XXXXXX)."
  type        = string
}

variable "region" {
  description = "Región de despliegue. Debe ser elegible para el Always Free Tier (us-west1, us-central1 o us-east1)."
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Zona del clúster GKE zonal, dentro de la región Free Tier."
  type        = string
  default     = "us-central1-a"
}

variable "notification_emails" {
  description = "Emails que reciben las alertas de presupuesto (60% y 70%)."
  type        = list(string)
}

variable "budget_amount_usd" {
  description = "Monto del presupuesto en USD, equivalente al 90% del valor estimado de la capa gratuita consumida."
  type        = number
  default     = 9
}

variable "mp_secret_names" {
  description = "Nombres de los secretos de Mercado Pago/app a crear en Secret Manager (valores placeholder)."
  type        = list(string)
  default     = ["mercadopago-access-token", "mercadopago-public-key", "mercadopago-webhook-secret"]
}

variable "compute_cpu_quota_cap" {
  description = "Techo duro de vCPUs (Compute Engine, todas las regiones) para evitar escalado fuera de la capa gratuita."
  type        = number
  default     = 4
}
