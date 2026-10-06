from decimal import Decimal

import pytest
from tests.fakes import FakeDispatcher, FakeGateway

from gestor.application.use_cases import CancelOrder, CreateOrder, RequestPayment
from gestor.domain.exceptions import InvalidPaymentRequest, OrderNotCancelable
from gestor.domain.models import Order, OrderStatus, PaymentRequest


def test_request_payment_dispatches_with_default_terminal():
    dispatcher = FakeDispatcher()

    queued = RequestPayment(dispatcher, "TERM_DEFAULT").execute(
        amount=Decimal("99.90"), description="Agua caliente"
    )

    assert queued.task_id == "task-1"
    assert dispatcher.dispatched == [queued.request]
    assert queued.request.terminal_id == "TERM_DEFAULT"


def test_request_payment_prefers_explicit_terminal():
    queued = RequestPayment(FakeDispatcher(), "TERM_DEFAULT").execute(
        amount=Decimal("10"), description="Agua", terminal_id="TERM_OTRA"
    )

    assert queued.request.terminal_id == "TERM_OTRA"


def test_request_payment_does_not_dispatch_invalid_requests():
    dispatcher = FakeDispatcher()

    with pytest.raises(InvalidPaymentRequest):
        RequestPayment(dispatcher, None).execute(amount=Decimal("10"), description="Agua")

    assert dispatcher.dispatched == []


def test_create_order_sends_request_to_gateway():
    gateway = FakeGateway()
    request = PaymentRequest.create(amount="10", description="Agua", terminal_id="T1")

    order = CreateOrder(gateway).execute(request)

    assert gateway.created == [request]
    assert order.status is OrderStatus.CREATED


def test_cancel_order_when_still_created():
    gateway = FakeGateway({"ORD1": Order(id="ORD1", status=OrderStatus.CREATED)})

    order = CancelOrder(gateway).execute("ORD1")

    assert order.status is OrderStatus.CANCELED
    assert gateway.canceled == ["ORD1"]


@pytest.mark.parametrize("status", [OrderStatus.AT_TERMINAL, OrderStatus.PROCESSED])
def test_cancel_order_rejected_once_terminal_took_it(status):
    gateway = FakeGateway({"ORD1": Order(id="ORD1", status=status)})

    with pytest.raises(OrderNotCancelable):
        CancelOrder(gateway).execute("ORD1")

    assert gateway.canceled == []
