import hashlib
import hmac

from simulador.infrastructure.signature import HmacSignatureVerifier, build_manifest

SECRET = "secreto-de-prueba"


def header_for(manifest: str, ts: str = "1704908010000", secret: str = SECRET) -> str:
    digest = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return f"ts={ts},v1={digest}"


def test_manifest_follows_mercadopago_template():
    manifest = build_manifest(data_id="ORD01ABC", request_id="req-1", ts="1704908010000")

    assert manifest == "id:ord01abc;request-id:req-1;ts:1704908010000;"


def test_manifest_omits_missing_request_id():
    assert build_manifest(data_id="ord1", request_id=None, ts="1") == "id:ord1;ts:1;"


def test_valid_signature_is_accepted():
    header = header_for("id:ord01abc;request-id:req-1;ts:1704908010000;")

    assert HmacSignatureVerifier(SECRET).is_valid(
        signature_header=header, request_id="req-1", data_id="ORD01ABC"
    )


def test_signature_for_another_order_is_rejected():
    header = header_for("id:ord01abc;request-id:req-1;ts:1704908010000;")

    assert not HmacSignatureVerifier(SECRET).is_valid(
        signature_header=header, request_id="req-1", data_id="ORD99"
    )


def test_signature_with_wrong_secret_is_rejected():
    header = header_for("id:ord01abc;request-id:req-1;ts:1704908010000;", secret="otro")

    assert not HmacSignatureVerifier(SECRET).is_valid(
        signature_header=header, request_id="req-1", data_id="ORD01ABC"
    )


def test_missing_or_malformed_header_is_rejected():
    verifier = HmacSignatureVerifier(SECRET)

    for header in (None, "", "basura", "ts=1", "v1=abc"):
        assert not verifier.is_valid(signature_header=header, request_id="r", data_id="ORD1")


def test_empty_secret_never_validates():
    header = header_for("id:ord1;request-id:r;ts:1;", ts="1", secret="")

    assert not HmacSignatureVerifier("").is_valid(
        signature_header=header, request_id="r", data_id="ORD1"
    )
