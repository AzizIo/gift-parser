from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str
    admin_id: int
    database_path: str = "data/gift_parser.sqlite3"
    log_level: str = "INFO"


settings = Settings()
