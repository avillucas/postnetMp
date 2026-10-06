from __future__ import annotations

from typing import Protocol

from simulador.domain.models import TransactionRecord


class SignatureVerifier(Protocol):
    def is_valid(
        self, *, signature_header: str | None, request_id: str | None, data_id: str
    ) -> bool: ...


class Dispenser(Protocol):
    """Actuador físico: el relé/válvula que entrega el agua."""

    def pulse(self, order_id: str, duration_ms: int) -> None: ...


class TransactionJournal(Protocol):
    def record(self, entry: TransactionRecord) -> None: ...

    def was_dispensed(self, order_id: str) -> bool: ...

    def recent(self, limit: int) -> list[TransactionRecord]: ...
