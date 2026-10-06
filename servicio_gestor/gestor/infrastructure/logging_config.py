import logging

AUDIT_LOGGER_NAME = "gestor.audit"


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    # httpx loguea cada request a nivel INFO; la auditoría ya lo cubre.
    logging.getLogger("httpx").setLevel(logging.WARNING)
