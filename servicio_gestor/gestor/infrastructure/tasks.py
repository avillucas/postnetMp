"""Tareas Celery: adaptador de entrada del worker."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from gestor.application.use_cases import CreateOrder
from gestor.domain.exceptions import GatewayError
from gestor.domain.models import Order, OrderStatus, PaymentRequest
from gestor.infrastructure.celery_app import app
from gestor.infrastructure.container import get_gateway

MAX_RETRIES = 3


def request_to_dict(request: PaymentRequest) -> dict[str, Any]:
    return {
        "amount": request.amount_as_string,
        "description": request.description,
        "external_reference": request.external_reference,
        "terminal_id": request.terminal_id,
        "idempotency_key": request.idempotency_key,
    }


def order_to_dict(order: Order) -> dict[str, Any]:
    return {
        "id": order.id,
        "status": order.status.value,
        "status_detail": order.status_detail,
        "external_reference": order.external_reference,
        "amount": str(order.amount) if order.amount is not None else None,
        "terminal_id": order.terminal_id,
    }


def order_from_dict(data: dict[str, Any]) -> Order:
    amount = data.get("amount")
    return Order(
        id=data["id"],
        status=OrderStatus.from_raw(data.get("status")),
        status_detail=data.get("status_detail"),
        external_reference=data.get("external_reference"),
        amount=Decimal(amount) if amount is not None else None,
        terminal_id=data.get("terminal_id"),
    )


@app.task(bind=True, name="gestor.create_order", max_retries=MAX_RETRIES)
def create_order_task(self, payload: dict[str, Any]) -> dict[str, Any]:
    request = PaymentRequest.create(**payload)
    try:
        order = CreateOrder(get_gateway()).execute(request)
    except GatewayError as exc:
        if exc.retryable:
            # Se reintenta con la misma idempotency_key: MP no duplica la orden.
            raise self.retry(exc=exc, countdown=2**self.request.retries) from exc
        raise
    return order_to_dict(order)
