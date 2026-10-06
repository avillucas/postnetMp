from gestor.domain.exceptions import OrderNotFound
from gestor.domain.models import Order, OrderStatus, PaymentRequest
from gestor.domain.ports import DispatchStatus


class FakeDispatcher:
    def __init__(self):
        self.dispatched: list[PaymentRequest] = []
        self.statuses: dict[str, DispatchStatus] = {}

    def dispatch(self, request: PaymentRequest) -> str:
        self.dispatched.append(request)
        return f"task-{len(self.dispatched)}"

    def status(self, task_id: str) -> DispatchStatus:
        return self.statuses.get(task_id, DispatchStatus(task_id=task_id, state="PENDING"))


class FakeGateway:
    def __init__(self, orders: dict[str, Order] | None = None):
        self.orders = orders or {}
        self.created: list[PaymentRequest] = []
        self.canceled: list[str] = []

    def create_order(self, request: PaymentRequest) -> Order:
        self.created.append(request)
        order = Order(
            id="ORD0001",
            status=OrderStatus.CREATED,
            external_reference=request.external_reference,
            amount=request.amount,
            terminal_id=request.terminal_id,
        )
        self.orders[order.id] = order
        return order

    def get_order(self, order_id: str) -> Order:
        try:
            return self.orders[order_id]
        except KeyError:
            raise OrderNotFound("Orden inexistente", status_code=404) from None

    def cancel_order(self, order_id: str, idempotency_key: str) -> Order:
        self.canceled.append(order_id)
        return Order(id=order_id, status=OrderStatus.CANCELED)
