from datetime import UTC, datetime

import pytest
from tests.fakes import InMemoryJournal, SpyDispenser

from simulador.application.use_cases import HandlePaymentNotification
from simulador.domain.models import Outcome, PaymentNotification

FIXED_NOW = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def paid(order_id: str = "ORD1", **overrides) -> PaymentNotification:
    params = {
        "order_id": order_id,
        "action": "order.processed",
        "status": "processed",
        "status_detail": "accredited",
        "total_paid_amount": "150.00",
    }
    params.update(overrides)
    return PaymentNotification(**params)


@pytest.fixture
def journal():
    return InMemoryJournal()


@pytest.fixture
def dispenser():
    return SpyDispenser()


@pytest.fixture
def handler(journal, dispenser):
    return HandlePaymentNotification(journal, dispenser, pulse_ms=500, clock=lambda: FIXED_NOW)


def test_accredited_payment_authorizes_dispense():
    assert paid().authorizes_dispense is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"action": "order.canceled", "status": "canceled", "status_detail": "canceled"},
        {"action": "order.failed", "status": "failed", "status_detail": "rejected"},
        {"action": "order.action_required", "status": "at_terminal"},
        {"status": "created"},
        {"status_detail": "in_process"},
        {"status": None, "status_detail": None},
    ],
)
def test_anything_but_accredited_payment_does_not_authorize(overrides):
    assert paid(**overrides).authorizes_dispense is False


def test_paid_order_triggers_one_pulse_and_is_recorded(handler, journal, dispenser):
    outcome = handler.execute(paid())

    assert outcome is Outcome.DISPENSED
    assert dispenser.pulses == [("ORD1", 500)]
    (entry,) = journal.entries
    assert entry.outcome is Outcome.DISPENSED
    assert entry.pulse_ms == 500
    assert entry.timestamp == FIXED_NOW.isoformat()
    assert entry.total_paid_amount == "150.00"


def test_retried_notification_does_not_dispense_twice(handler, journal, dispenser):
    handler.execute(paid())

    outcome = handler.execute(paid())

    assert outcome is Outcome.DUPLICATE
    assert len(dispenser.pulses) == 1
    assert [entry.outcome for entry in journal.entries] == [Outcome.DISPENSED, Outcome.DUPLICATE]


def test_different_orders_dispense_independently(handler, dispenser):
    handler.execute(paid("ORD1"))
    handler.execute(paid("ORD2"))

    assert [order_id for order_id, _ in dispenser.pulses] == ["ORD1", "ORD2"]


def test_unpaid_notification_is_logged_without_pulse(handler, journal, dispenser):
    outcome = handler.execute(paid(action="order.canceled", status="canceled"))

    assert outcome is Outcome.IGNORED
    assert dispenser.pulses == []
    assert journal.entries[0].outcome is Outcome.IGNORED
    assert journal.entries[0].pulse_ms is None
