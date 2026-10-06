"""Adaptador de salida: log de transacciones en un archivo JSON Lines."""

from __future__ import annotations

import json
import threading
from collections import deque
from dataclasses import asdict
from pathlib import Path

from simulador.domain.models import Outcome, TransactionRecord


class JsonlTransactionJournal:
    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        # Se reconstruye desde el archivo para no dispensar dos veces tras un reinicio.
        self._dispensed = {
            entry.order_id for entry in self._read_all() if entry.outcome is Outcome.DISPENSED
        }

    def record(self, entry: TransactionRecord) -> None:
        with self._lock:
            with self._path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
            if entry.outcome is Outcome.DISPENSED:
                self._dispensed.add(entry.order_id)

    def was_dispensed(self, order_id: str) -> bool:
        with self._lock:
            return order_id in self._dispensed

    def recent(self, limit: int) -> list[TransactionRecord]:
        with self._lock:
            return list(deque(self._read_all(), maxlen=limit))

    def _read_all(self) -> list[TransactionRecord]:
        if not self._path.exists():
            return []
        entries = []
        with self._path.open(encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    data = json.loads(line)
                    data["outcome"] = Outcome(data["outcome"])
                    entries.append(TransactionRecord(**data))
        return entries
