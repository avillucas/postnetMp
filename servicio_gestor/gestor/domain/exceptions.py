class DomainError(Exception):
    """Error de reglas de negocio."""


class InvalidPaymentRequest(DomainError):
    pass


class OrderNotCancelable(DomainError):
    pass


class GatewayError(Exception):
    """Falla al hablar con el proveedor de pagos.

    `retryable` indica si tiene sentido reintentar (red, 5xx, 429).
    """

    def __init__(self, message: str, *, status_code: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class OrderNotFound(GatewayError):
    pass


class DispatchError(Exception):
    """No se pudo encolar la tarea (broker caído)."""
