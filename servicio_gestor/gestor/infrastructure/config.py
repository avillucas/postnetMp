from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.local", extra="ignore")

    mp_access_token: str = ""
    mp_terminal_id: str = ""
    mp_api_base_url: str = "https://api.mercadopago.com"
    mp_order_expiration: str = "PT10M"
    mp_print_on_terminal: str = "no_ticket"
    mp_timeout_seconds: float = 10.0
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
