"""Puertos: contratos que el dominio/aplicación exige a la infraestructura."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from gestor.domain.models import Order, PaymentRequest


class PaymentGateway(Protocol):
    def create_order(self, request: PaymentRequest) -> Order: ...

    def get_order(self, order_id: str) -> Order: ...

    def cancel_order(self, order_id: str, idempotency_key: str) -> Order: ...


@dataclass(frozen=True)
class DispatchStatus:
    task_id: str
    state: str
    order: Order | None = None
    error: str | None = None


class PaymentDispatcher(Protocol):
    """Encola el envío de la orden para no bloquear la API."""

    def dispatch(self, request: PaymentRequest) -> str: ...

    def status(self, task_id: str) -> DispatchStatus: ...
