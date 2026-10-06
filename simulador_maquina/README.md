# Simulador de Máquina Expendedora

Servicio FastAPI independiente que representa a la máquina. Expone el webhook que recibe las
notificaciones de Mercado Pago, valida la firma del evento y, si el pago fue acreditado,
registra la transacción y simula el pulso de dispensado.

## Arquitectura hexagonal

```
simulador/
├── domain/
│   ├── models.py      PaymentNotification (regla de dispensado), TransactionRecord, Outcome
│   └── ports.py       SignatureVerifier, Dispenser, TransactionJournal
├── application/
│   └── use_cases.py   HandlePaymentNotification
└── infrastructure/
    ├── api/           Entrada HTTP (FastAPI + Pydantic)
    ├── signature.py   Validación HMAC de x-signature
    ├── journal.py     Log de transacciones (JSON Lines)
    ├── dispenser.py   Pulso simulado (logger)
    └── config.py      Variables de entorno
```

Para conectar una máquina real alcanza con reemplazar `LoggingDispenser` por un adaptador que
accione el relé.

## Reglas de negocio

| Notificación                                                           | Resultado   | Pulso |
| ---------------------------------------------------------------------- | ----------- | ----- |
| `order.processed` con `status=processed` y `status_detail=accredited`  | `dispensed` | Sí    |
| La misma orden otra vez (reintento de Mercado Pago)                    | `duplicate` | No    |
| Cualquier otro evento (`order.canceled`, `order.failed`, etc.)         | `ignored`   | No    |

Todas las notificaciones con firma válida quedan en el log, incluso las ignoradas. Las órdenes
ya dispensadas se recuperan del archivo al iniciar, así un reinicio no provoca un segundo pulso.

## Variables de entorno

Se leen de `.env.local` en la raíz del repositorio.

| Variable                     | Descripción                                             | Default                    |
| ---------------------------- | ------------------------------------------------------- | -------------------------- |
| `MP_WEBHOOK_SECRET`          | Clave secreta de Webhooks de la aplicación              | —                          |
| `WEBHOOK_SIGNATURE_REQUIRED` | `false` acepta webhooks sin firma (solo pruebas locales) | `true`                     |
| `DISPENSE_PULSE_MS`          | Duración del pulso simulado                             | `500`                      |
| `TRANSACTION_LOG_PATH`       | Archivo del log de transacciones                        | `/data/transactions.jsonl` |
| `LOG_LEVEL`                  | Nivel del logger                                        | `INFO`                     |

Si `MP_WEBHOOK_SECRET` está vacío y la firma es obligatoria, todos los webhooks se rechazan.

## Levantar el servicio

Desde la raíz del repositorio:

```bash
cp .env.local.example .env.local
docker compose up --build simulador-maquina
```

- Servicio: http://localhost:8001
- Documentación interactiva (OpenAPI): http://localhost:8001/docs

## Endpoints

| Método | Ruta                    | Descripción                                             |
| ------ | ----------------------- | ------------------------------------------------------- |
| `POST` | `/webhooks/mercadopago` | Webhook del tópico Order. Responde `{"result": "..."}`. |
| `GET`  | `/transactions?limit=N` | Últimas transacciones registradas.                      |
| `GET`  | `/health`               | Chequeo de vida.                                        |

Respuestas del webhook: `200` evento aceptado, `401` firma inválida, `400` el `data.id` de la
URL no coincide con el del body, `422` payload mal formado.

## Validación de la firma

Mercado Pago envía `x-signature: ts=<ts>,v1=<hash>` y `x-request-id`. El simulador recalcula
el HMAC-SHA256 con `MP_WEBHOOK_SECRET` sobre:

```
id:<data.id en minúsculas>;request-id:<x-request-id>;ts:<ts>;
```

y lo compara en tiempo constante con `v1`.

## Probar

### 1. Webhook firmado localmente (sin Mercado Pago)

El script firma con el mismo algoritmo que Mercado Pago y no necesita dependencias:

```bash
docker compose exec simulador-maquina python scripts/send_test_webhook.py --order-id ORD123
# 200 {"result":"dispensed"}

docker compose exec simulador-maquina python scripts/send_test_webhook.py --order-id ORD123
# 200 {"result":"duplicate"}

docker compose exec simulador-maquina python scripts/send_test_webhook.py \
  --action order.canceled --status canceled --status-detail canceled
# 200 {"result":"ignored"}
```

Verificar el resultado:

```bash
curl -s http://localhost:8001/transactions
docker compose logs simulador-maquina | grep "PULSO DE DISPENSADO"
docker compose exec simulador-maquina cat /data/transactions.jsonl
```

### 2. Notificaciones reales de Mercado Pago

Mercado Pago necesita una URL pública para llegar al contenedor:

```bash
ngrok http 8001      # o: cloudflared tunnel --url http://localhost:8001
```

En [Tus integraciones](https://www.mercadopago.com.ar/developers/panel/app) > tu aplicación >
**Webhooks**:

1. Configurar la URL de prueba `https://<tu-tunel>/webhooks/mercadopago`.
2. Suscribirse al evento **Order (Mercado Pago)**.
3. Copiar la **clave secreta** en `MP_WEBHOOK_SECRET` y reiniciar el servicio
   (`docker compose up -d simulador-maquina`).

Luego crear un cobro desde el [Servicio Gestor](../servicio_gestor/README.md) y pagarlo en la
terminal: el simulador registra `dispensed`.

## Pruebas automatizadas

```bash
cd simulador_maquina
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

pytest tests/unit          # reglas de dispensado e idempotencia
pytest tests/integration   # firma HMAC, webhook HTTP (httpx) y log en archivo
```
