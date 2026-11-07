from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str
    admin_id: int

    telegram_api_id: int
    telegram_api_hash: str
    telegram_phone: str | None = None
    telegram_session_path: str = "data/telegram_market"

    database_path: str = "data/gift_parser.sqlite3"
    poll_interval_seconds: int = 45
    request_delay_seconds: float = 0.25
    resale_page_size: int = 100
    log_level: str = "INFO"


settings = Settings()
