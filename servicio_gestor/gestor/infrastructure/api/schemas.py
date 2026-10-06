from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from gestor.domain.models import Order
from gestor.domain.ports import DispatchStatus


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2, examples=["150.00"])
    description: str = Field(min_length=1, max_length=150, examples=["Agua caliente 1L"])
    external_reference: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9_-]{1,64}$",
        description="Identificador propio de la venta. Si se omite, se genera uno.",
    )
    terminal_id: str | None = Field(
        default=None,
        description="Terminal Point destino. Si se omite, se usa MP_TERMINAL_ID.",
    )


class PaymentQueued(BaseModel):
    task_id: str
    status: str = "queued"
    external_reference: str
    amount: Decimal
    terminal_id: str


class OrderOut(BaseModel):
    id: str
    status: str
    status_detail: str | None = None
    external_reference: str | None = None
    amount: Decimal | None = None
    terminal_id: str | None = None

    @classmethod
    def from_domain(cls, order: Order) -> OrderOut:
        return cls(
            id=order.id,
            status=order.status.value,
            status_detail=order.status_detail,
            external_reference=order.external_reference,
            amount=order.amount,
            terminal_id=order.terminal_id,
        )


class PaymentTaskStatus(BaseModel):
    task_id: str
    state: str = Field(description="Estado Celery: PENDING, STARTED, RETRY, SUCCESS o FAILURE.")
    order: OrderOut | None = None
    error: str | None = None

    @classmethod
    def from_domain(cls, status: DispatchStatus) -> PaymentTaskStatus:
        return cls(
            task_id=status.task_id,
            state=status.state,
            order=OrderOut.from_domain(status.order) if status.order else None,
            error=status.error,
        )
