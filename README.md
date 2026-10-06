# Expendedora de agua caliente + Mercado Pago Point

Entorno local con Docker que simula el cobro de una máquina expendedora a través de una
terminal Point, usando la API de Orders de Mercado Pago con credenciales de prueba.

```
cliente ──POST /api/v1/payments──▶ gestor-api ──tarea──▶ Redis ──▶ gestor-worker
                                                                        │ POST /v1/orders
                                                                        ▼
simulador-maquina ◀──webhook order.processed── Mercado Pago ◀── terminal Point (pago)
   └─ valida firma, registra la transacción y simula el pulso de dispensado
```

| Servicio            | Puerto | Documentación                                        |
| ------------------- | ------ | ---------------------------------------------------- |
| `gestor-api`        | 8000   | [servicio_gestor/README.md](servicio_gestor/README.md) |
| `gestor-worker`     | —      | [servicio_gestor/README.md](servicio_gestor/README.md) |
| `simulador-maquina` | 8001   | [simulador_maquina/README.md](simulador_maquina/README.md) |
| `redis`             | —      | Broker y backend de resultados de Celery             |

## Puesta en marcha

```bash
cp .env.local.example .env.local   # completar MP_ACCESS_TOKEN, MP_TERMINAL_ID y MP_WEBHOOK_SECRET
docker compose up --build
```

Si los puertos 8000 u 8001 están ocupados en el host, se pueden cambiar al levantar:

```bash
GESTOR_PORT=18000 SIMULADOR_PORT=18001 docker compose up --build
```

`.env` y `.env.local` están excluidos por `.gitignore`; solo se versiona `.env.local.example`.

## Calidad

```bash
pip install -r requirements-lint.txt
ruff check . && flake8 . && black --check .
```

Las pruebas se corren por servicio (ver cada README). El pipeline de GitHub Actions
([.github/workflows/ci.yml](.github/workflows/ci.yml)) ejecuta linting, pruebas unitarias,
pruebas de integración y el build de las imágenes.
