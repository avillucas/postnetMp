"""Casos de uso: orquestan el dominio a través de los puertos."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from gestor.domain.exceptions import OrderNotCancelable
from gestor.domain.models import Order, PaymentRequest
from gestor.domain.ports import DispatchStatus, PaymentDispatcher, PaymentGateway


@dataclass(frozen=True)
class QueuedPayment:
    task_id: str
    request: PaymentRequest


class RequestPayment:
    """Valida el cobro y lo encola; la API responde sin esperar a Mercado Pago."""

    def __init__(self, dispatcher: PaymentDispatcher, default_terminal_id: str | None):
        self._dispatcher = dispatcher
        self._default_terminal_id = default_terminal_id

    def execute(
        self,
        *,
        amount: Decimal,
        description: str,
        external_reference: str | None = None,
        terminal_id: str | None = None,
    ) -> QueuedPayment:
        request = PaymentRequest.create(
            amount=amount,
            description=description,
            external_reference=external_reference,
            terminal_id=terminal_id or self._default_terminal_id,
        )
        task_id = self._dispatcher.dispatch(request)
        return QueuedPayment(task_id=task_id, request=request)


class GetPaymentStatus:
    def __init__(self, dispatcher: PaymentDispatcher):
        self._dispatcher = dispatcher

    def execute(self, task_id: str) -> DispatchStatus:
        return self._dispatcher.status(task_id)


class CreateOrder:
    """Lo ejecuta el worker: envía la orden a la terminal Point."""

    def __init__(self, gateway: PaymentGateway):
        self._gateway = gateway

    def execute(self, request: PaymentRequest) -> Order:
        return self._gateway.create_order(request)


class GetOrder:
    def __init__(self, gateway: PaymentGateway):
        self._gateway = gateway

    def execute(self, order_id: str) -> Order:
        return self._gateway.get_order(order_id)


class CancelOrder:
    def __init__(self, gateway: PaymentGateway):
        self._gateway = gateway

    def execute(self, order_id: str) -> Order:
        order = self._gateway.get_order(order_id)
        if not order.is_cancelable:
            raise OrderNotCancelable(
                f"La orden {order_id} está en estado '{order.status}' y no puede cancelarse"
            )
        return self._gateway.cancel_order(order_id, idempotency_key=str(uuid.uuid4()))
