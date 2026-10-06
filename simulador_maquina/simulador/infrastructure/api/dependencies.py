from functools import lru_cache

from simulador.application.use_cases import HandlePaymentNotification
from simulador.domain.ports import SignatureVerifier, TransactionJournal
from simulador.infrastructure.config import get_settings
from simulador.infrastructure.dispenser import LoggingDispenser
from simulador.infrastructure.journal import JsonlTransactionJournal
from simulador.infrastructure.signature import AllowAllVerifier, HmacSignatureVerifier


@lru_cache
def get_journal() -> TransactionJournal:
    return JsonlTransactionJournal(get_settings().transaction_log_path)


@lru_cache
def get_handler() -> HandlePaymentNotification:
    return HandlePaymentNotification(
        journal=get_journal(),
        dispenser=LoggingDispenser(),
        pulse_ms=get_settings().dispense_pulse_ms,
    )


@lru_cache
def get_verifier() -> SignatureVerifier:
    settings = get_settings()
    if not settings.webhook_signature_required:
        return AllowAllVerifier()
    return HmacSignatureVerifier(settings.mp_webhook_secret)
