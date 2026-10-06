"""Adaptador de salida: API de Orders de Mercado Pago para terminales Point."""

from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from gestor.domain.exceptions import GatewayError, OrderNotFound
from gestor.domain.models import Order, OrderStatus, PaymentRequest
from gestor.infrastructure.logging_config import AUDIT_LOGGER_NAME

audit = logging.getLogger(AUDIT_LOGGER_NAME)

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class MercadoPagoOrdersGateway:
    def __init__(
        self,
        *,
        access_token: str,
        base_url: str = "https://api.mercadopago.com",
        expiration_time: str = "PT10M",
        print_on_terminal: str = "no_ticket",
        timeout: float = 10.0,
        client: httpx.Client | None = None,
    ):
        self._access_token = access_token
        self._expiration_time = expiration_time
        self._print_on_terminal = print_on_terminal
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout)

    def create_order(self, request: PaymentRequest) -> Order:
        payload = {
            "type": "point",
            "external_reference": request.external_reference,
            "description": request.description,
            "expiration_time": self._expiration_time,
            "transactions": {"payments": [{"amount": request.amount_as_string}]},
            "config": {
                "point": {
                    "terminal_id": request.terminal_id,
                    "print_on_terminal": self._print_on_terminal,
                }
            },
        }
        body = self._send(
            "POST", "/v1/orders", idempotency_key=request.idempotency_key, payload=payload
        )
        return _to_order(body)

    def get_order(self, order_id: str) -> Order:
        return _to_order(self._send("GET", f"/v1/orders/{order_id}"))

    def cancel_order(self, order_id: str, idempotency_key: str) -> Order:
        body = self._send("POST", f"/v1/orders/{order_id}/cancel", idempotency_key=idempotency_key)
        return _to_order(body)

    def _send(
        self,
        method: str,
        path: str,
        *,
        idempotency_key: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self._access_token:
            raise GatewayError("MP_ACCESS_TOKEN no está configurado")
        headers = {"Authorization": f"Bearer {self._access_token}"}
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        # Se audita el payload, nunca los headers: llevan el access token.
        audit.info(
            "MP request %s %s idempotency_key=%s payload=%s",
            method,
            path,
            idempotency_key,
            json.dumps(payload, ensure_ascii=False) if payload is not None else None,
        )
        try:
            response = self._client.request(method, path, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            audit.error("MP request %s %s falló sin respuesta: %r", method, path, exc)
            raise GatewayError(
                f"No se pudo contactar a Mercado Pago: {exc}", retryable=True
            ) from exc

        audit.info(
            "MP response %s %s status=%s body=%s", method, path, response.status_code, response.text
        )

        if response.status_code == 404:
            raise OrderNotFound("Orden inexistente en Mercado Pago", status_code=404)
        if response.is_error:
            raise GatewayError(
                f"Mercado Pago respondió {response.status_code}: {response.text}",
                status_code=response.status_code,
                retryable=response.status_code in _RETRYABLE_STATUS,
            )
        try:
            return response.json()
        except ValueError as exc:
            raise GatewayError("Respuesta de Mercado Pago no es JSON válido") from exc


def _to_order(body: dict[str, Any]) -> Order:
    order_id = body.get("id")
    if not order_id:
        raise GatewayError("La respuesta de Mercado Pago no incluye el id de la orden")

    payments = (body.get("transactions") or {}).get("payments") or []
    point_config = (body.get("config") or {}).get("point") or {}
    return Order(
        id=str(order_id),
        status=OrderStatus.from_raw(body.get("status")),
        status_detail=body.get("status_detail"),
        external_reference=body.get("external_reference"),
        amount=_to_decimal(payments[0].get("amount")) if payments else None,
        terminal_id=point_config.get("terminal_id"),
    )


def _to_decimal(raw: Any) -> Decimal | None:
    if raw is None:
        return None
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        return None
