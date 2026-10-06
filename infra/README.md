# Despliegue en Producción - Capa Gratuita de GCP

Arquitectura: **FastAPI Payment API** (Cloud Run) + **Celery Workers / Redis**
(GKE, clúster zonal de 1 nodo `e2-micro`) + **Secret Manager** + **Cloud Build**.
Todo dimensionado para no salir del Always Free Tier.

Este directorio contiene solo infraestructura (Terraform + manifiestos K8s +
pipeline de CI/CD). Se asume que el código de la app vive en `./api`
(FastAPI) y `./worker` (Celery), cada uno con su propio `Dockerfile`.

## Por qué estas decisiones de Free Tier

| Servicio | Decisión | Motivo |
|---|---|---|
| Cloud Run | `min-instances=0`, `max-instances=2`, `cpu-idle` | Escala a cero, techo duro de instancias, CPU no se cobra en reposo |
| GKE | Clúster **zonal estándar** (no Autopilot), 1 nodo `e2-micro`, sin autoscaling | 1 clúster zonal/Autopilot sin costo de gestión por cuenta de billing + nodo `e2-micro` dentro del Always Free de Compute Engine (solo en `us-west1`, `us-central1`, `us-east1`) |
| Redis/Celery | `ResourceQuota` + `LimitRange` + réplicas fijas en 1 | Evita que el namespace consuma más de lo que el único nodo puede dar |
| Secret Manager | 3 secretos, 1 versión activa c/u | Dentro de las 6 versiones activas / 10.000 accesos gratis por mes |
| Cloud Build | `timeout: 600s` por build, sin triggers concurrentes | Cap duro para no superar los 120 min/día gratis |
| Billing Budget | Monto = 90% del valor estimado de Free Tier, alertas a 60% y 70% | Aviso temprano antes de llegar al límite gratuito |

## 0. Prerrequisitos locales

```bash
gcloud components install kubectl gke-gcloud-auth-plugin
gcloud auth login
```

## 1. Crear el proyecto y vincular Billing

```bash
# Variables de trabajo
export PROJECT_ID="postnetmp-prod"
export BILLING_ACCOUNT_ID="XXXXXX-XXXXXX-XXXXXX"   # gcloud billing accounts list
export ORG_ID=""                                    # opcional, si usás una organización
export REGION="us-central1"
export ZONE="us-central1-a"

# Crear el proyecto (omitir --organization si no aplica)
gcloud projects create "$PROJECT_ID" --name="PostnetMp Prod" ${ORG_ID:+--organization="$ORG_ID"}

# Vincular la cuenta de Billing (obligatorio para habilitar APIs de pago)
gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT_ID"

gcloud config set project "$PROJECT_ID"
```

## 2. Desplegar la infraestructura con Terraform

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars con project_id, billing_account_id, notification_emails, etc.

terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

Esto crea: APIs habilitadas, Artifact Registry, service accounts con permisos
mínimos, clúster GKE zonal + node pool `e2-micro`, secretos placeholder,
servicio de Cloud Run, presupuesto con alertas al 60%/70% y el intento de
cap de cuota de vCPUs.

> Verificar manualmente en **Console > IAM y administración > Cuotas** que el
> override de `compute.googleapis.com/cpus` haya quedado aplicado; algunas
> métricas requieren ajustarse ahí directamente si el override vía API falla.

## 3. Cargar los valores reales de los secretos

Terraform solo crea los secretos con un valor placeholder. Cargar los reales:

```bash
echo -n "APP_USR-xxxxxxxx" | gcloud secrets versions add mercadopago-access-token \
  --data-file=- --project="$PROJECT_ID"

echo -n "APP_USR-yyyyyyyy" | gcloud secrets versions add mercadopago-public-key \
  --data-file=- --project="$PROJECT_ID"

echo -n "whsec_zzzzzzzz" | gcloud secrets versions add mercadopago-webhook-secret \
  --data-file=- --project="$PROJECT_ID"
```

## 4. Aplicar los manifiestos de Kubernetes (primer despliegue manual)

```bash
gcloud container clusters get-credentials postnetmp-zonal --zone="$ZONE" --project="$PROJECT_ID"

export REGION="$REGION" PROJECT_ID="$PROJECT_ID" IMAGE_TAG="latest"
for f in infra/k8s/*.yaml; do
  envsubst '$${PROJECT_ID} $${REGION} $${IMAGE_TAG}' < "$f" | kubectl apply -f -
done

kubectl -n expendedora get pods
```

> Requiere que las imágenes `payment-api` y `celery-worker` ya existan en
> Artifact Registry (ver paso 6) antes del primer `apply`.

## 5. Conectar el repositorio y crear el trigger de Cloud Build

La conexión a GitHub requiere un flujo OAuth interactivo, por eso se hace con
`gcloud` en lugar de Terraform:

```bash
gcloud builds connections create github postnetmp-connection \
  --project="$PROJECT_ID" --region="$REGION"
# Seguir el link que imprime el comando para autorizar la GitHub App.

gcloud builds connections repositories create postnetmp-repo \
  --connection=postnetmp-connection --region="$REGION" \
  --remote-uri="https://github.com/<owner>/<repo>.git"

gcloud builds triggers create github \
  --name="postnetmp-deploy" \
  --region="$REGION" \
  --repository="projects/$PROJECT_ID/locations/$REGION/connections/postnetmp-connection/repositories/postnetmp-repo" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml" \
  --service-account="projects/$PROJECT_ID/serviceAccounts/cicd-deployer-sa@${PROJECT_ID}.iam.gserviceaccount.com"
```

## 6. Build y despliegue manual inicial (antes del primer push)

```bash
gcloud auth configure-docker "${REGION}-docker.pkg.dev"

docker build -t "${REGION}-docker.pkg.dev/${PROJECT_ID}/postnetmp-images/payment-api:latest" ./api
docker build -t "${REGION}-docker.pkg.dev/${PROJECT_ID}/postnetmp-images/celery-worker:latest" ./worker

docker push "${REGION}-docker.pkg.dev/${PROJECT_ID}/postnetmp-images/payment-api:latest"
docker push "${REGION}-docker.pkg.dev/${PROJECT_ID}/postnetmp-images/celery-worker:latest"
```

Luego de este push inicial, re-ejecutar el paso 4 para que los Deployments
tomen las imágenes reales.

## 7. Verificación de los topes de la capa gratuita

```bash
# Instancias y escalado de Cloud Run
gcloud run services describe payment-api --region="$REGION" \
  --format="value(spec.template.metadata.annotations)"

# Nodos y pods del clúster (debe haber 1 nodo e2-micro)
kubectl get nodes -o wide
kubectl -n expendedora describe resourcequota free-tier-quota

# Presupuesto y alertas configuradas
gcloud billing budgets list --billing-account="$BILLING_ACCOUNT_ID"

# Minutos de Cloud Build consumidos hoy
gcloud builds list --project="$PROJECT_ID" --filter="createTime>=$(date -u +%Y-%m-%dT00:00:00Z)" \
  --format="table(id,status,createTime,duration)"
```

## Notas de seguridad

- Ningún service account usa roles `Owner`/`Editor`: permisos acotados por
  recurso (`iam.tf`).
- Los secretos de Mercado Pago nunca se guardan en YAML ni en el repo: se
  inyectan en Cloud Run vía `secret_key_ref` y en GKE vía el driver CSI de
  Secret Manager + Workload Identity (no se decodifican en `etcd` como texto
  plano salvo el `Secret` sincronizado que el CSI driver genera para
  consumo del pod).
- Revisar y ajustar `roles/run.invoker: allUsers` en `cloud_run.tf` si el
  endpoint de pagos no debe ser público.
