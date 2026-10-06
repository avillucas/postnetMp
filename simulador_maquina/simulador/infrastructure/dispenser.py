import logging

logger = logging.getLogger("simulador.dispenser")


class LoggingDispenser:
    """Simula el pulso de dispensado; en la máquina real accionaría el relé."""

    def pulse(self, order_id: str, duration_ms: int) -> None:
        logger.info("PULSO DE DISPENSADO order_id=%s duracion_ms=%s", order_id, duration_ms)
