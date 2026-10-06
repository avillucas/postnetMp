from decimal import Decimal

import pytest

from gestor.domain.exceptions import InvalidPaymentRequest
from gestor.domain.models import Order, OrderStatus, PaymentRequest


def make_request(**overrides):
    params = {"amount": "150", "description": "Agua caliente 1L", "terminal_id": "TERM_1"}
    params.update(overrides)
    return PaymentRequest.create(**params)


def test_create_normalizes_amount_and_generates_identifiers():
    request = make_request()

    assert request.amount == Decimal("150.00")
    assert request.amount_as_string == "150.00"
    assert request.external_reference.startswith("exp-")
    assert request.idempotency_key


def test_each_request_gets_a_distinct_idempotency_key():
    assert make_request().idempotency_key != make_request().idempotency_key


def test_create_keeps_given_reference_and_idempotency_key():
    request = make_request(external_reference="venta-42", idempotency_key="key-1")

    assert request.external_reference == "venta-42"
    assert request.idempotency_key == "key-1"


@pytest.mark.parametrize("amount", ["0", "-5", "10.555", "abc", "NaN", "Infinity"])
def test_create_rejects_invalid_amounts(amount):
    with pytest.raises(InvalidPaymentRequest):
        make_request(amount=amount)


@pytest.mark.parametrize("description", ["", "   ", "x" * 151])
def test_create_rejects_invalid_descriptions(description):
    with pytest.raises(InvalidPaymentRequest):
        make_request(description=description)


@pytest.mark.parametrize("reference", ["", "con espacios", "a" * 65, "ñandú"])
def test_create_rejects_invalid_external_reference(reference):
    with pytest.raises(InvalidPaymentRequest):
        make_request(external_reference=reference)


@pytest.mark.parametrize("terminal_id", [None, "", "  "])
def test_create_requires_terminal(terminal_id):
    with pytest.raises(InvalidPaymentRequest):
        make_request(terminal_id=terminal_id)


def test_unknown_status_does_not_break_parsing():
    assert OrderStatus.from_raw("estado_nuevo") is OrderStatus.UNKNOWN
    assert OrderStatus.from_raw(None) is OrderStatus.UNKNOWN


@pytest.mark.parametrize(
    ("status", "cancelable", "final"),
    [
        (OrderStatus.CREATED, True, False),
        (OrderStatus.AT_TERMINAL, False, False),
        (OrderStatus.PROCESSED, False, True),
        (OrderStatus.CANCELED, False, True),
        (OrderStatus.EXPIRED, False, True),
    ],
)
def test_order_lifecycle_rules(status, cancelable, final):
    order = Order(id="ORD1", status=status)

    assert order.is_cancelable is cancelable
    assert order.is_final is final
