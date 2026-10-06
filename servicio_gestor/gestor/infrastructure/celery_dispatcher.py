"""Adaptador de salida: encola cobros en Celery/Redis."""

from __future__ import annotations

from celery.result import AsyncResult
from kombu.exceptions import OperationalError
from redis.exceptions import RedisError

from gestor.domain.exceptions import DispatchError
from gestor.domain.models import PaymentRequest
from gestor.domain.ports import DispatchStatus
from gestor.infrastructure.celery_app import app
from gestor.infrastructure.tasks import create_order_task, order_from_dict, request_to_dict


class CeleryPaymentDispatcher:
    def dispatch(self, request: PaymentRequest) -> str:
        try:
            result = create_order_task.delay(request_to_dict(request))
        except (OperationalError, RedisError, ConnectionError) as exc:
            raise DispatchError(f"No se pudo encolar el cobro: {exc}") from exc
        return result.id

    def status(self, task_id: str) -> DispatchStatus:
        try:
            result = AsyncResult(task_id, app=app)
            state = result.state
            value = result.result
        except (OperationalError, RedisError, ConnectionError) as exc:
            raise DispatchError(f"No se pudo consultar la tarea: {exc}") from exc

        if state == "SUCCESS":
            return DispatchStatus(task_id=task_id, state=state, order=order_from_dict(value))
        if state == "FAILURE":
            return DispatchStatus(task_id=task_id, state=state, error=str(value))
        return DispatchStatus(task_id=task_id, state=state)
