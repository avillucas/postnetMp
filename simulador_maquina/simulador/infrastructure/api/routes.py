import logging
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from simulador.application.use_cases import HandlePaymentNotification
from simulador.domain.ports import SignatureVerifier, TransactionJournal
from simulador.infrastructure.api.dependencies import get_handler, get_journal, get_verifier
from simulador.infrastructure.api.schemas import TransactionOut, WebhookPayload, WebhookResult

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhooks/mercadopago", response_model=WebhookResult)
def mercadopago_webhook(
    payload: WebhookPayload,
    handler: Annotated[HandlePaymentNotification, Depends(get_handler)],
    verifier: Annotated[SignatureVerifier, Depends(get_verifier)],
    x_signature: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
    data_id: Annotated[str | None, Query(alias="data.id")] = None,
) -> WebhookResult:
    # MP firma el data.id de la query string; el del body es solo respaldo.
    signed_id = data_id or payload.data.id
    if not verifier.is_valid(
        signature_header=x_signature, request_id=x_request_id, data_id=signed_id
    ):
        logger.warning("Webhook rechazado por firma inválida order_id=%s", payload.data.id)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Firma inválida")
    if data_id and data_id.lower() != payload.data.id.lower():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "data.id no coincide con el body")

    outcome = handler.execute(payload.to_domain())
    logger.info(
        "Webhook action=%s order_id=%s resultado=%s", payload.action, payload.data.id, outcome
    )
    return WebhookResult(result=outcome.value)


@router.get("/transactions", response_model=list[TransactionOut])
def transactions(
    journal: Annotated[TransactionJournal, Depends(get_journal)],
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[TransactionOut]:
    """Últimas transacciones registradas, para verificar las pruebas."""
    return [TransactionOut(**asdict(entry)) for entry in journal.recent(limit)]
