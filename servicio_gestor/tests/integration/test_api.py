import pytest
from fastapi.testclient import TestClient
from tests.fakes import FakeDispatcher, FakeGateway

from gestor.domain.exceptions import DispatchError, GatewayError
from gestor.domain.models import Order, OrderStatus
from gestor.domain.ports import DispatchStatus
from gestor.infrastructure.api.dependencies import get_dispatcher, get_payment_gateway
from gestor.infrastructure.api.main import app
from gestor.infrastructure.config import Settings, get_settings


@pytest.fixture
def dispatcher():
    return FakeDispatcher()


@pytest.fixture
def gateway():
    return FakeGateway()


@pytest.fixture
def client(dispatcher, gateway):
    app.dependency_overrides[get_dispatcher] = lambda: dispatcher
    app.dependency_overrides[get_payment_gateway] = lambda: gateway
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, mp_terminal_id="TERM_DEFAULT"
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_post_payment_queues_and_returns_202(client, dispatcher):
    response = client.post(
        "/api/v1/payments", json={"amount": "150.00", "description": "Agua caliente 1L"}
    )

    assert response.status_code == 202
    body = response.json()
    assert body["task_id"] == "task-1"
    assert body["status"] == "queued"
    assert body["terminal_id"] == "TERM_DEFAULT"
    assert body["external_reference"] == dispatcher.dispatched[0].external_reference


@pytest.mark.parametrize(
    "payload",
    [
        {"amount": "0", "description": "Agua"},
        {"amount": "10.999", "description": "Agua"},
        {"amount": "10", "description": ""},
        {"amount": "10", "description": "Agua", "external_reference": "con espacios"},
        {"description": "Agua"},
    ],
)
def test_post_payment_validates_body(client, dispatcher, payload):
    response = client.post("/api/v1/payments", json=payload)

    assert response.status_code == 422
    assert dispatcher.dispatched == []


def test_post_payment_returns_503_when_broker_is_down(client, dispatcher):
    def fail(request):
        raise DispatchError("redis caído")

    dispatcher.dispatch = fail

    response = client.post("/api/v1/payments", json={"amount": "10", "description": "Agua"})

    assert response.status_code == 503


def test_payment_status_exposes_created_order(client, dispatcher):
    dispatcher.statuses["task-1"] = DispatchStatus(
        task_id="task-1", state="SUCCESS", order=Order(id="ORD1", status=OrderStatus.CREATED)
    )

    body = client.get("/api/v1/payments/task-1").json()

    assert body["state"] == "SUCCESS"
    assert body["order"]["id"] == "ORD1"


def test_get_order(client, gateway):
    gateway.orders["ORD1"] = Order(id="ORD1", status=OrderStatus.AT_TERMINAL)

    response = client.get("/api/v1/orders/ORD1")

    assert response.status_code == 200
    assert response.json()["status"] == "at_terminal"


def test_get_order_not_found(client):
    assert client.get("/api/v1/orders/ORDX").status_code == 404


def test_get_order_rejects_non_alphanumeric_id(client):
    assert client.get("/api/v1/orders/ORD-1.x").status_code == 422


def test_cancel_order(client, gateway):
    gateway.orders["ORD1"] = Order(id="ORD1", status=OrderStatus.CREATED)

    response = client.post("/api/v1/orders/ORD1/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "canceled"


def test_cancel_order_conflict_when_not_cancelable(client, gateway):
    gateway.orders["ORD1"] = Order(id="ORD1", status=OrderStatus.PROCESSED)

    assert client.post("/api/v1/orders/ORD1/cancel").status_code == 409


def test_gateway_failure_maps_to_502(client, gateway):
    def fail(order_id):
        raise GatewayError("MP caído", status_code=500, retryable=True)

    gateway.get_order = fail

    assert client.get("/api/v1/orders/ORD1").status_code == 502
