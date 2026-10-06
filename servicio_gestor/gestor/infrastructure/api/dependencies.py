from functools import lru_cache

from gestor.domain.ports import PaymentDispatcher, PaymentGateway
from gestor.infrastructure.container import get_gateway


@lru_cache
def get_dispatcher() -> PaymentDispatcher:
    # Import diferido: evita crear la app Celery al importar la API en tests.
    from gestor.infrastructure.celery_dispatcher import CeleryPaymentDispatcher

    return CeleryPaymentDispatcher()


def get_payment_gateway() -> PaymentGateway:
    return get_gateway()
