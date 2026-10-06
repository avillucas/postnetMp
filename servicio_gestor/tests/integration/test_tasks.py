import pytest
from tests.fakes import FakeGateway

from gestor.domain.exceptions import GatewayError
from gestor.domain.models import PaymentRequest
from gestor.infrastructure import tasks


@pytest.fixture
def payload():
    request = PaymentRequest.create(
        amount="150", description="Agua", terminal_id="T1", idempotency_key="idem-1"
    )
    return tasks.request_to_dict(request)


def test_task_creates_order_and_returns_serializable_result(monkeypatch, payload):
    gateway = FakeGateway()
    monkeypatch.setattr(tasks, "get_gateway", lambda: gateway)

    result = tasks.create_order_task.apply(args=[payload])

    assert result.successful()
    assert result.result["id"] == "ORD0001"
    assert result.result["status"] == "created"
    assert gateway.created[0].idempotency_key == "idem-1"
    assert tasks.order_from_dict(result.result).amount == gateway.created[0].amount


def test_task_fails_without_retry_on_non_retryable_error(monkeypatch, payload):
    gateway = FakeGateway()
    calls = []

    def fail(request):
        calls.append(request)
        raise GatewayError("401", status_code=401, retryable=False)

    gateway.create_order = fail
    monkeypatch.setattr(tasks, "get_gateway", lambda: gateway)

    result = tasks.create_order_task.apply(args=[payload])

    assert result.failed()
    assert len(calls) == 1
