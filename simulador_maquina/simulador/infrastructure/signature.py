"""Validación de la firma `x-signature` de los webhooks de Mercado Pago."""

from __future__ import annotations

import hashlib
import hmac


def build_manifest(*, data_id: str, request_id: str | None, ts: str) -> str:
    # Plantilla oficial: "id:[data.id];request-id:[x-request-id];ts:[ts];".
    # Los valores ausentes se omiten; un data.id alfanumérico va en minúsculas.
    manifest = f"id:{data_id.lower()};"
    if request_id:
        manifest += f"request-id:{request_id};"
    return manifest + f"ts:{ts};"


def sign(secret: str, manifest: str) -> str:
    return hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()


def parse_signature_header(header: str) -> tuple[str | None, str | None]:
    parts = dict(
        (key.strip(), value.strip())
        for key, _, value in (item.partition("=") for item in header.split(","))
    )
    return parts.get("ts"), parts.get("v1")


class HmacSignatureVerifier:
    def __init__(self, secret: str):
        self._secret = secret

    def is_valid(
        self, *, signature_header: str | None, request_id: str | None, data_id: str
    ) -> bool:
        if not self._secret or not signature_header or not data_id:
            return False
        ts, received = parse_signature_header(signature_header)
        if not ts or not received:
            return False
        expected = sign(self._secret, build_manifest(data_id=data_id, request_id=request_id, ts=ts))
        return hmac.compare_digest(expected, received)


class AllowAllVerifier:
    """Solo para pruebas manuales locales (WEBHOOK_SIGNATURE_REQUIRED=false)."""

    def is_valid(
        self, *, signature_header: str | None, request_id: str | None, data_id: str
    ) -> bool:
        return True
