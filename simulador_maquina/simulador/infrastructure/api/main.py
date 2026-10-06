import logging

from fastapi import FastAPI

from simulador.infrastructure.api.routes import router
from simulador.infrastructure.config import get_settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    if not settings.webhook_signature_required:
        logger.warning("Validación de firma DESACTIVADA: no usar fuera de pruebas locales")
    elif not settings.mp_webhook_secret:
        logger.warning("MP_WEBHOOK_SECRET vacío: todos los webhooks serán rechazados")

    app = FastAPI(title="Simulador de Máquina Expendedora", version="1.0.0")
    app.include_router(router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
