"""Reglas de negocio de la expendedora. Sin dependencias externas."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

PROCESSED_ACTION = "order.processed"
PROCESSED_STATUS = "processed"
ACCREDITED_DETAIL = "accredited"


class Outcome(StrEnum):
    DISPENSED = "dispensed"
    DUPLICATE = "duplicate"
    IGNORED = "ignored"


@dataclass(frozen=True)
class PaymentNotification:
    order_id: str
    action: str
    status: str | None = None
    status_detail: str | None = None
    external_reference: str | None = None
    total_paid_amount: str | None = None
    live_mode: bool = False

    @property
    def authorizes_dispense(self) -> bool:
        """Solo un pago procesado y acreditado habilita la entrega de agua."""
        return (
            self.action == PROCESSED_ACTION
            and self.status == PROCESSED_STATUS
            and self.status_detail == ACCREDITED_DETAIL
        )


@dataclass(frozen=True)
class TransactionRecord:
    timestamp: str
    outcome: Outcome
    order_id: str
    action: str
    status: str | None
    status_detail: str | None
    external_reference: str | None
    total_paid_amount: str | None
    live_mode: bool
    pulse_ms: int | None = None
