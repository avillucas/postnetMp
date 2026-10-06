import json
import logging
from decimal import Decimal

import httpx
import pytest

from gestor.domain.exceptions import GatewayError, OrderNotFound
from gestor.domain.models import OrderStatus, PaymentRequest
from gestor.infrastructure.logging_config import AUDIT_LOGGER_NAME
from gestor.infrastructure.mercadopago_gateway import MercadoPagoOrdersGateway

ORDER_BODY = {
    "id": "ORD01JABC",
    "type": "point",
    "status": "created",
    "status_detail": "created",
    "external_reference": "venta-1",
    "transactions": {"payments": [{"id": "PAY01", "amount": "150.00", "status": "created"}]},
    "config": {"point": {"terminal_id": "TERM_1", "print_on_terminal": "no_ticket"}},
}


def make_gateway(handler) -> MercadoPagoOrdersGateway:
    client = httpx.Client(
        base_url="https://api.mercadopago.com", transport=httpx.MockTransport(handler)
    )
    return MercadoPagoOrdersGateway(access_token="TEST-token", client=client)


def make_request() -> PaymentRequest:
    return PaymentRequest.create(
        amount="150",
        description="Agua caliente 1L",
        terminal_id="TERM_1",
        external_reference="venta-1",
        idempotency_key="idem-1",
    )


def test_create_order_sends_point_order_payload():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(201, json=ORDER_BODY)

    order = make_gateway(handler).create_order(make_request())

    (request,) = seen
    assert request.method == "POST"
    assert request.url.path == "/v1/orders"
    assert request.headers["Authorization"] == "Bearer TEST-token"
    assert request.headers["X-Idempotency-Key"] == "idem-1"
    assert json.loads(request.content) == {
        "type": "point",
        "external_reference": "venta-1",
        "description": "Agua caliente 1L",
        "expiration_time": "PT10M",
        "transactions": {"payments": [{"amount": "150.00"}]},
        "config": {"point": {"terminal_id": "TERM_1", "print_on_terminal": "no_ticket"}},
    }
    assert order.id == "ORD01JABC"
    assert order.status is OrderStatus.CREATED
    assert order.amount == Decimal("150.00")
    assert order.terminal_id == "TERM_1"


def test_get_and_cancel_hit_expected_endpoints():
    paths: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append((request.method, request.url.path))
        return httpx.Response(200, json={**ORDER_BODY, "status": "canceled"})

    gateway = make_gateway(handler)
    gateway.get_order("ORD01JABC")
    canceled = gateway.cancel_order("ORD01JABC", idempotency_key="idem-2")

    assert paths == [("GET", "/v1/orders/ORD01JABC"), ("POST", "/v1/orders/ORD01JABC/cancel")]
    assert canceled.status is OrderStatus.CANCELED


@pytest.mark.parametrize(
    ("status_code", "retryable"), [(400, False), (401, False), (429, True), (503, True)]
)
def test_http_errors_are_classified_for_retry(status_code, retryable):
    gateway = make_gateway(lambda request: httpx.Response(status_code, json={"errors": []}))

    with pytest.raises(GatewayError) as excinfo:
        gateway.create_order(make_request())

    assert excinfo.value.status_code == status_code
    assert excinfo.value.retryable is retryable


def test_network_failure_is_retryable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red", request=request)

    with pytest.raises(GatewayError) as excinfo:
        make_gateway(handler).create_order(make_request())

    assert excinfo.value.retryable is True


def test_missing_order_raises_not_found():
    gateway = make_gateway(lambda request: httpx.Response(404, json={}))

    with pytest.raises(OrderNotFound):
        gateway.get_order("ORDX")


def test_audit_log_records_payload_and_response_without_token(caplog):
    gateway = make_gateway(lambda request: httpx.Response(201, json=ORDER_BODY))

    with caplog.at_level(logging.INFO, logger=AUDIT_LOGGER_NAME):
        gateway.create_order(make_request())

    assert "venta-1" in caplog.text
    assert "ORD01JABC" in caplog.text
    assert "TEST-token" not in caplog.text


def test_missing_access_token_fails_fast_without_calling_mercadopago():
    calls = []
    client = httpx.Client(
        base_url="https://api.mercadopago.com",
        transport=httpx.MockTransport(lambda request: calls.append(request)),
    )
    gateway = MercadoPagoOrdersGateway(access_token="", client=client)

    with pytest.raises(GatewayError) as excinfo:
        gateway.create_order(make_request())

    assert excinfo.value.retryable is False
    assert calls == []
