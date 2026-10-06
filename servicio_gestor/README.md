# Servicio Gestor (API de Pagos)

API FastAPI que crea y gestiona órdenes de pago en una terminal Point mediante la API de
Orders de Mercado Pago. Es stateless: no tiene base de datos. El envío de la orden se delega
a un worker Celery (Redis como broker) para que la API responda de inmediato.

## Arquitectura hexagonal

```
gestor/
├── domain/            Reglas de negocio puras
│   ├── models.py        PaymentRequest, Order, OrderStatus
│   ├── ports.py         PaymentGateway, PaymentDispatcher
│   └── exceptions.py
├── application/
│   └── use_cases.py     RequestPayment, CreateOrder, GetOrder, CancelOrder, GetPaymentStatus
└── infrastructure/    Adaptadores
    ├── api/                     Entrada HTTP (FastAPI + Pydantic)
    ├── tasks.py                 Entrada del worker (Celery)
    ├── celery_dispatcher.py     Salida: encola en Redis
    ├── mercadopago_gateway.py   Salida: API de Orders (httpx)
    ├── container.py             Composición de adaptadores
    └── config.py                Variables de entorno
```

El dominio y los casos de uso no importan FastAPI, Celery ni httpx.

## Variables de entorno

Se leen de `.env.local` en la raíz del repositorio (ver `.env.local.example`).

| Variable               | Descripción                                                    | Default                      |
| ---------------------- | -------------------------------------------------------------- | ---------------------------- |
| `MP_ACCESS_TOKEN`      | Access token de prueba de la aplicación                        | —                            |
| `MP_TERMINAL_ID`       | Terminal Point por defecto                                     | —                            |
| `MP_API_BASE_URL`      | URL base de la API                                             | `https://api.mercadopago.com` |
| `MP_ORDER_EXPIRATION`  | Vigencia de la orden en la terminal (ISO 8601)                 | `PT10M`                      |
| `MP_PRINT_ON_TERMINAL` | Impresión de ticket en la terminal                             | `no_ticket`                  |
| `MP_TIMEOUT_SECONDS`   | Timeout de las llamadas a Mercado Pago                         | `10`                         |
| `REDIS_URL`            | Broker y backend de resultados de Celery                       | `redis://redis:6379/0`       |
| `LOG_LEVEL`            | Nivel del logger                                               | `INFO`                       |

### Preparar el entorno de prueba en Mercado Pago

1. Crear una aplicación en [Tus integraciones](https://www.mercadopago.com.ar/developers/panel/app)
   y copiar el access token de las **credenciales de prueba** en `MP_ACCESS_TOKEN`.
2. Vincular la terminal Point a la cuenta de prueba y ponerla en modo integrado (PDV).
3. Obtener el identificador de la terminal y cargarlo en `MP_TERMINAL_ID`:

   ```bash
   curl -H "Authorization: Bearer $MP_ACCESS_TOKEN" https://api.mercadopago.com/terminals/v1/list
   ```

## Levantar el servicio

Desde la raíz del repositorio:

```bash
cp .env.local.example .env.local
docker compose up --build gestor-api gestor-worker
```

- API: http://localhost:8000
- Documentación interactiva (OpenAPI): http://localhost:8000/docs

## Endpoints

| Método | Ruta                               | Descripción                                             |
| ------ | ---------------------------------- | ------------------------------------------------------- |
| `POST` | `/api/v1/payments`                 | Valida y encola el cobro. Responde `202` con `task_id`. |
| `GET`  | `/api/v1/payments/{task_id}`       | Estado de la tarea y, si terminó, la orden creada.      |
| `GET`  | `/api/v1/orders/{order_id}`        | Consulta la orden en Mercado Pago.                      |
| `POST` | `/api/v1/orders/{order_id}/cancel` | Cancela la orden (solo en estado `created`).            |
| `GET`  | `/health`                          | Chequeo de vida.                                        |

## Probar el flujo

```bash
# 1. Solicitar el cobro: la API responde al instante
curl -s -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{"amount": "150.00", "description": "Agua caliente 1L"}'
# {"task_id":"<task_id>","status":"queued","external_reference":"exp-...","amount":"150.00","terminal_id":"..."}

# 2. Consultar el resultado del envío a la terminal
curl -s http://localhost:8000/api/v1/payments/<task_id>
# {"task_id":"...","state":"SUCCESS","order":{"id":"ORD...","status":"created",...},"error":null}

# 3. Consultar o cancelar la orden
curl -s http://localhost:8000/api/v1/orders/<order_id>
curl -s -X POST http://localhost:8000/api/v1/orders/<order_id>/cancel
```

Al pagar en la terminal, Mercado Pago notifica el resultado al
[Simulador de Máquina](../simulador_maquina/README.md).

Estados de `state`: `PENDING` (en cola o `task_id` desconocido), `STARTED`, `RETRY`,
`SUCCESS`, `FAILURE` (el detalle queda en `error`).

### Comportamiento ante fallas

- Errores de red, `429` y `5xx` de Mercado Pago: el worker reintenta hasta 3 veces con
  espera exponencial, reutilizando la misma `X-Idempotency-Key` para no duplicar la orden.
- Errores `4xx` (credenciales, terminal inválida): la tarea termina en `FAILURE` sin reintentos.
- Redis caído: `POST /api/v1/payments` responde `503`.

## Auditoría

El logger `gestor.audit` registra cada payload saliente y cada respuesta de Mercado Pago.
Los headers no se loguean porque contienen el access token.

```bash
docker compose logs -f gestor-worker gestor-api | grep gestor.audit
```

## Pruebas

```bash
cd servicio_gestor
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

pytest tests/unit          # lógica de dominio y casos de uso
pytest tests/integration   # adaptadores: gateway (httpx.MockTransport), API y tarea Celery
```

Las pruebas no requieren Redis ni credenciales: no hacen llamadas reales a Mercado Pago.
