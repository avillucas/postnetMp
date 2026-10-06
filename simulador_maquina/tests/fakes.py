from simulador.domain.models import Outcome, TransactionRecord


class InMemoryJournal:
    def __init__(self):
        self.entries: list[TransactionRecord] = []

    def record(self, entry: TransactionRecord) -> None:
        self.entries.append(entry)

    def was_dispensed(self, order_id: str) -> bool:
        return any(
            entry.order_id == order_id and entry.outcome is Outcome.DISPENSED
            for entry in self.entries
        )

    def recent(self, limit: int) -> list[TransactionRecord]:
        return self.entries[-limit:]


class SpyDispenser:
    def __init__(self):
        self.pulses: list[tuple[str, int]] = []

    def pulse(self, order_id: str, duration_ms: int) -> None:
        self.pulses.append((order_id, duration_ms))
