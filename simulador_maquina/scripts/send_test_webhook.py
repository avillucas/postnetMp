"""Envía al simulador un webhook firmado igual que lo haría Mercado Pago.

Uso:
    MP_WEBHOOK_SECRET=... python scripts/send_test_webhook.py --order-id ORD123
"""

import argparse
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8001/webhooks/mercadopago")
    parser.add_argument("--secret", default=os.environ.get("MP_WEBHOOK_SECRET", ""))
    parser.add_argument("--order-id", default=f"ORD{uuid.uuid4().hex[:20].upper()}")
    parser.add_argument("--action", default="order.processed")
    parser.add_argument("--status", default="processed")
    parser.add_argument("--status-detail", default="accredited")
    parser.add_argument("--amount", default="150.00")
    args = parser.parse_args()

    request_id = str(uuid.uuid4())
    ts = str(int(time.time() * 1000))
    manifest = f"id:{args.order_id.lower()};request-id:{request_id};ts:{ts};"
    v1 = hmac.new(args.secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()

    body = {
        "action": args.action,
        "type": "order",
        "live_mode": False,
        "data": {
            "id": args.order_id,
            "status": args.status,
            "status_detail": args.status_detail,
            "external_reference": "prueba-local",
            "total_paid_amount": args.amount,
        },
    }
    query = urllib.parse.urlencode({"data.id": args.order_id, "type": "order"})
    request = urllib.request.Request(
        f"{args.url}?{query}",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "x-signature": f"ts={ts},v1={v1}",
            "x-request-id": request_id,
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            print(response.status, response.read().decode())
    except urllib.error.HTTPError as exc:
        print(exc.code, exc.read().decode())
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
