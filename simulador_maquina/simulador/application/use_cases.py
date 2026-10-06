from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime

from simulador.domain.models import Outcome, PaymentNotification, TransactionRecord
from simulador.domain.ports import Dispenser, TransactionJournal


class HandlePaymentNotification:
    """Decide si corresponde dispensar y deja registro de cada notificación."""

    def __init__(
        self,
        journal: TransactionJournal,
        dispenser: Dispenser,
        pulse_ms: int,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self._journal = journal
        self._dispenser = dispenser
        self._pulse_ms = pulse_ms
        self._clock = clock
        # Mercado Pago reintenta webhooks: evita dos pulsos por reintentos simultáneos.
        self._lock = threading.Lock()

    def execute(self, notification: PaymentNotification) -> Outcome:
        with self._lock:
            outcome = self._decide(notification)
            if outcome is Outcome.DISPENSED:
                self._dispenser.pulse(notification.order_id, self._pulse_ms)
            self._journal.record(self._to_record(notification, outcome))
        return outcome

    def _decide(self, notification: PaymentNotification) -> Outcome:
        if not notification.authorizes_dispense:
            return Outcome.IGNORED
        if self._journal.was_dispensed(notification.order_id):
            return Outcome.DUPLICATE
        return Outcome.DISPENSED

    def _to_record(self, notification: PaymentNotification, outcome: Outcome) -> TransactionRecord:
        return TransactionRecord(
            timestamp=self._clock().isoformat(),
            outcome=outcome,
            order_id=notification.order_id,
            action=notification.action,
            status=notification.status,
            status_detail=notification.status_detail,
            external_reference=notification.external_reference,
            total_paid_amount=notification.total_paid_amount,
            live_mode=notification.live_mode,
            pulse_ms=self._pulse_ms if outcome is Outcome.DISPENSED else None,
        )
