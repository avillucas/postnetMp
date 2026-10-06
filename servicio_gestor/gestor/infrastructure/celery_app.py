from celery import Celery
from celery.signals import setup_logging

from gestor.infrastructure.config import get_settings
from gestor.infrastructure.logging_config import configure_logging

settings = get_settings()

app = Celery(
    "gestor",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["gestor.infrastructure.tasks"],
)
app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)


@setup_logging.connect
def _configure_worker_logging(**kwargs) -> None:
    # Mismo formato que la API: el log de auditoría conserva el nombre del logger.
    configure_logging(settings.log_level)
