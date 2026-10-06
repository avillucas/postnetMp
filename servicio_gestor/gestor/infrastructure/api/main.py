import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from gestor.domain.exceptions import (
    DispatchError,
    GatewayError,
    InvalidPaymentRequest,
    OrderNotCancelable,
    OrderNotFound,
)
from gestor.infrastructure.api.routes import router
from gestor.infrastructure.config import get_settings
from gestor.infrastructure.logging_config import configure_logging

logger = logging.getLogger(__name__)

_ERROR_STATUS: dict[type[Exception], int] = {
    InvalidPaymentRequest: 422,
    OrderNotCancelable: 409,
    OrderNotFound: 404,
    GatewayError: 502,
    DispatchError: 503,
}


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    if not settings.mp_access_token:
        logger.warning("MP_ACCESS_TOKEN no está configurado: Mercado Pago rechazará las órdenes")

    app = FastAPI(title="Servicio Gestor - Pagos Point", version="1.0.0")
    app.include_router(router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    for exc_type, status_code in _ERROR_STATUS.items():
        app.add_exception_handler(exc_type, _handler_for(status_code))

    return app


def _handler_for(status_code: int):
    async def handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handler


app = create_app()
