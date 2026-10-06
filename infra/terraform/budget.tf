data "google_billing_account" "account" {
  billing_account = var.billing_account_id
}

resource "google_monitoring_notification_channel" "budget_email" {
  for_each = toset(var.notification_emails)

  project      = var.project_id
  display_name = "Free Tier Budget Alert - ${each.value}"
  type         = "email"

  labels = {
    email_address = each.value
  }
}

resource "google_billing_budget" "free_tier_guard" {
  billing_account = data.google_billing_account.account.id
  display_name    = "postnetmp-free-tier-guard"

  budget_filter {
    projects = ["projects/${var.project_id}"]
  }

  # Monto equivalente al 90% del valor estimado de la capa gratuita consumida.
  amount {
    specified_amount {
      currency_code = "USD"
      units         = var.budget_amount_usd
    }
  }

  # Umbrales estrictos de notificación: 60% y 70% del presupuesto.
  threshold_rules {
    threshold_percent = 0.6
    spend_basis       = "CURRENT_SPEND"
  }
  threshold_rules {
    threshold_percent = 0.7
    spend_basis       = "CURRENT_SPEND"
  }

  all_updates_rule {
    monitoring_notification_channels = [for c in google_monitoring_notification_channel.budget_email : c.id]
    disable_default_iam_recipients   = false
  }
}
