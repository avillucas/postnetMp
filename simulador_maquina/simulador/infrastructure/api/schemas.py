from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from simulador.domain.models import PaymentNotification


class WebhookData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    status: str | None = None
    status_detail: str | None = None
    external_reference: str | None = None
    total_paid_amount: str | None = None


class WebhookPayload(BaseModel):
    """Notificación del tópico Order de Mercado Pago."""

    model_config = ConfigDict(extra="ignore")

    action: str = Field(min_length=1, examples=["order.processed"])
    type: str = Field(examples=["order"])
    data: WebhookData
    live_mode: bool = False

    def to_domain(self) -> PaymentNotification:
        return PaymentNotification(
            order_id=self.data.id,
            action=self.action,
            status=self.data.status,
            status_detail=self.data.status_detail,
            external_reference=self.data.external_reference,
            total_paid_amount=self.data.total_paid_amount,
            live_mode=self.live_mode,
        )


class WebhookResult(BaseModel):
    result: str = Field(description="dispensed, duplicate o ignored")


class TransactionOut(BaseModel):
    timestamp: str
    outcome: str
    order_id: str
    action: str
    status: str | None
    status_detail: str | None
    external_reference: str | None
    total_paid_amount: str | None
    live_mode: bool
    pulse_ms: int | None
