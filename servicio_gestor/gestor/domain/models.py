"""Entidades y objetos de valor del dominio de pagos. Sin dependencias externas."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from gestor.domain.exceptions import InvalidPaymentRequest

_TWO_PLACES = Decimal("0.01")
_EXTERNAL_REFERENCE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_MAX_DESCRIPTION_LENGTH = 150


class OrderStatus(StrEnum):
    CREATED = "created"
    AT_TERMINAL = "at_terminal"
    PROCESSED = "processed"
    ACTION_REQUIRED = "action_required"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    FAILED = "failed"
    EXPIRED = "expired"
    UNKNOWN = "unknown"

    @classmethod
    def from_raw(cls, raw: str | None) -> OrderStatus:
        try:
            return cls(raw)
        except ValueError:
            return cls.UNKNOWN


_FINAL_STATUSES = frozenset(
    {
        OrderStatus.PROCESSED,
        OrderStatus.CANCELED,
        OrderStatus.REFUNDED,
        OrderStatus.FAILED,
        OrderStatus.EXPIRED,
    }
)


@dataclass(frozen=True)
class PaymentRequest:
    """Intención de cobro que todavía no fue enviada a la terminal."""

    amount: Decimal
    description: str
    external_reference: str
    terminal_id: str
    idempotency_key: str

    @classmethod
    def create(
        cls,
        *,
        amount: Decimal | str | int,
        description: str,
        terminal_id: str | None,
        external_reference: str | None = None,
        idempotency_key: str | None = None,
    ) -> PaymentRequest:
        return cls(
            amount=_validated_amount(amount),
            description=_validated_description(description),
            external_reference=_validated_reference(external_reference),
            terminal_id=_validated_terminal(terminal_id),
            idempotency_key=idempotency_key or str(uuid.uuid4()),
        )

    @property
    def amount_as_string(self) -> str:
        """Formato que exige la API de Orders: string con dos decimales."""
        return f"{self.amount:.2f}"


@dataclass(frozen=True)
class Order:
    """Orden ya registrada en Mercado Pago."""

    id: str
    status: OrderStatus
    status_detail: str | None = None
    external_reference: str | None = None
    amount: Decimal | None = None
    terminal_id: str | None = None

    @property
    def is_final(self) -> bool:
        return self.status in _FINAL_STATUSES

    @property
    def is_cancelable(self) -> bool:
        """Solo se puede cancelar por API mientras la terminal no tomó la orden."""
        return self.status is OrderStatus.CREATED


def _validated_amount(raw: Decimal | str | int) -> Decimal:
    try:
        amount = Decimal(str(raw))
    except InvalidOperation as exc:
        raise InvalidPaymentRequest(f"Monto inválido: {raw!r}") from exc
    if not amount.is_finite() or amount <= 0:
        raise InvalidPaymentRequest("El monto debe ser mayor a cero")
    if amount != amount.quantize(_TWO_PLACES):
        raise InvalidPaymentRequest("El monto admite como máximo dos decimales")
    return amount.quantize(_TWO_PLACES)


def _validated_description(raw: str) -> str:
    description = (raw or "").strip()
    if not description:
        raise InvalidPaymentRequest("La descripción es obligatoria")
    if len(description) > _MAX_DESCRIPTION_LENGTH:
        raise InvalidPaymentRequest(
            f"La descripción admite hasta {_MAX_DESCRIPTION_LENGTH} caracteres"
        )
    return description


def _validated_reference(raw: str | None) -> str:
    if raw is None:
        return f"exp-{uuid.uuid4().hex}"
    if not _EXTERNAL_REFERENCE_RE.match(raw):
        raise InvalidPaymentRequest(
            "external_reference admite hasta 64 caracteres: letras, números, '-' y '_'"
        )
    return raw


def _validated_terminal(raw: str | None) -> str:
    terminal_id = (raw or "").strip()
    if not terminal_id:
        raise InvalidPaymentRequest("No hay una terminal Point configurada para el cobro")
    return terminal_id
