from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from gestor.application.use_cases import CancelOrder, GetOrder, GetPaymentStatus, RequestPayment
from gestor.domain.ports import PaymentDispatcher, PaymentGateway
from gestor.infrastructure.api.dependencies import get_dispatcher, get_payment_gateway
from gestor.infrastructure.api.schemas import (
    OrderOut,
    PaymentCreate,
    PaymentQueued,
    PaymentTaskStatus,
)
from gestor.infrastructure.config import Settings, get_settings

router = APIRouter(prefix="/api/v1")

Dispatcher = Annotated[PaymentDispatcher, Depends(get_dispatcher)]
Gateway = Annotated[PaymentGateway, Depends(get_payment_gateway)]
# El id viaja en la URL hacia Mercado Pago: se restringe a alfanumérico.
OrderId = Annotated[str, Path(pattern=r"^[A-Za-z0-9]{1,64}$")]


@router.post("/payments", response_model=PaymentQueued, status_code=status.HTTP_202_ACCEPTED)
def request_payment(
    body: PaymentCreate,
    dispatcher: Dispatcher,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PaymentQueued:
    """Encola el cobro y responde de inmediato; el worker lo envía a la terminal."""
    queued = RequestPayment(dispatcher, settings.mp_terminal_id).execute(
        amount=body.amount,
        description=body.description,
        external_reference=body.external_reference,
        terminal_id=body.terminal_id,
    )
    return PaymentQueued(
        task_id=queued.task_id,
        external_reference=queued.request.external_reference,
        amount=queued.request.amount,
        terminal_id=queued.request.terminal_id,
    )


@router.get("/payments/{task_id}", response_model=PaymentTaskStatus)
def payment_status(task_id: str, dispatcher: Dispatcher) -> PaymentTaskStatus:
    """Resultado del envío. Un task_id desconocido figura como PENDING."""
    return PaymentTaskStatus.from_domain(GetPaymentStatus(dispatcher).execute(task_id))


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: OrderId, gateway: Gateway) -> OrderOut:
    return OrderOut.from_domain(GetOrder(gateway).execute(order_id))


@router.post("/orders/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: OrderId, gateway: Gateway) -> OrderOut:
    return OrderOut.from_domain(CancelOrder(gateway).execute(order_id))
