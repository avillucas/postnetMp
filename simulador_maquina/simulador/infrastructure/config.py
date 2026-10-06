from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.local", extra="ignore")

    mp_webhook_secret: str = ""
    webhook_signature_required: bool = True
    dispense_pulse_ms: int = 500
    transaction_log_path: str = "data/transactions.jsonl"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
