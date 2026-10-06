"""Composición de adaptadores. Único lugar que conoce las implementaciones concretas."""

from functools import lru_cache

from gestor.domain.ports import PaymentGateway
from gestor.infrastructure.config import get_settings
from gestor.infrastructure.mercadopago_gateway import MercadoPagoOrdersGateway


@lru_cache
def get_gateway() -> PaymentGateway:
    settings = get_settings()
    return MercadoPagoOrdersGateway(
        access_token=settings.mp_access_token,
        base_url=settings.mp_api_base_url,
        expiration_time=settings.mp_order_expiration,
        print_on_terminal=settings.mp_print_on_terminal,
        timeout=settings.mp_timeout_seconds,
    )
