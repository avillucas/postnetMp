import pytest
from fastapi.testclient import TestClient
from tests.fakes import SpyDispenser

from simulador.application.use_cases import HandlePaymentNotification
from simulador.infrastructure.api.dependencies import get_handler, get_journal, get_verifier
from simulador.infrastructure.api.main import app
from simulador.infrastructure.journal import JsonlTransactionJournal
from simulador.infrastructure.signature import HmacSignatureVerifier, build_manifest, sign

SECRET = "secreto-de-prueba"
TS = "1704908010000"
REQUEST_ID = "req-1"


def webhook_body(order_id="ORD01ABC", action="order.processed", status="processed"):
    return {
        "action": action,
        "type": "order",
        "live_mode": False,
        "application_id": "123",
        "data": {
            "id": order_id,
            "status": status,
            "status_detail": "accredited" if status == "processed" else status,
            "external_reference": "venta-1",
            "total_paid_amount": "150.00",
            "transactions": {"payments": [{"id": "PAY1", "amount": "150.00"}]},
        },
    }


def signed_headers(order_id="ORD01ABC", secret=SECRET):
    manifest = build_manifest(data_id=order_id, request_id=REQUEST_ID, ts=TS)
    return {"x-signature": f"ts={TS},v1={sign(secret, manifest)}", "x-request-id": REQUEST_ID}


def post_webhook(client, order_id="ORD01ABC", headers=None, **body_overrides):
    return client.post(
        "/webhooks/mercadopago",
        params={"data.id": order_id, "type": "order"},
        json=webhook_body(order_id, **body_overrides),
        headers=signed_headers(order_id) if headers is None else headers,
    )


@pytest.fixture
def dispenser():
    return SpyDispenser()


@pytest.fixture
def log_path(tmp_path):
    return tmp_path / "transactions.jsonl"


@pytest.fixture
def client(dispenser, log_path):
    journal = JsonlTransactionJournal(log_path)
    handler = HandlePaymentNotification(journal, dispenser, pulse_ms=500)
    app.dependency_overrides[get_journal] = lambda: journal
    app.dependency_overrides[get_handler] = lambda: handler
    app.dependency_overrides[get_verifier] = lambda: HmacSignatureVerifier(SECRET)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_signed_paid_webhook_dispenses_and_logs(client, dispenser, log_path):
    response = post_webhook(client)

    assert response.status_code == 200
    assert response.json() == {"result": "dispensed"}
    assert dispenser.pulses == [("ORD01ABC", 500)]
    assert '"order_id": "ORD01ABC"' in log_path.read_text()


def test_webhook_retry_is_acknowledged_without_second_pulse(client, dispenser):
    post_webhook(client)

    response = post_webhook(client)

    assert response.status_code == 200
    assert response.json() == {"result": "duplicate"}
    assert len(dispenser.pulses) == 1


def test_non_payment_event_is_acknowledged_and_ignored(client, dispenser):
    response = post_webhook(client, action="order.canceled", status="canceled")

    assert response.status_code == 200
    assert response.json() == {"result": "ignored"}
    assert dispenser.pulses == []


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"x-signature": "ts=1,v1=deadbeef", "x-request-id": REQUEST_ID},
        signed_headers(secret="otro-secreto"),
        signed_headers(order_id="ORDOTRA"),
    ],
)
def test_invalid_signature_is_rejected_without_side_effects(client, dispenser, log_path, headers):
    response = post_webhook(client, headers=headers)

    assert response.status_code == 401
    assert dispenser.pulses == []
    assert not log_path.exists()


def test_body_for_a_different_order_than_the_signed_one_is_rejected(client, dispenser):
    response = client.post(
        "/webhooks/mercadopago",
        params={"data.id": "ORD01ABC"},
        json=webhook_body("ORDOTRA"),
        headers=signed_headers("ORD01ABC"),
    )

    assert response.status_code == 400
    assert dispenser.pulses == []


def test_malformed_payload_is_rejected(client):
    response = client.post(
        "/webhooks/mercadopago", json={"action": "order.processed"}, headers=signed_headers()
    )

    assert response.status_code == 422


def test_transactions_endpoint_lists_log(client):
    post_webhook(client, order_id="ORD1")
    post_webhook(client, order_id="ORD2")

    entries = client.get("/transactions", params={"limit": 1}).json()

    assert [entry["order_id"] for entry in entries] == ["ORD2"]
    assert entries[0]["outcome"] == "dispensed"


def test_dispensed_orders_survive_restart(log_path, dispenser):
    first = JsonlTransactionJournal(log_path)
    HandlePaymentNotification(first, dispenser, pulse_ms=500).execute(
        webhook_payload_to_domain("ORD1")
    )

    assert JsonlTransactionJournal(log_path).was_dispensed("ORD1")


def webhook_payload_to_domain(order_id):
    from simulador.infrastructure.api.schemas import WebhookPayload

    return WebhookPayload(**webhook_body(order_id)).to_domain()
