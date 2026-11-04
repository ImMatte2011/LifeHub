from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    database_url_sync: str
    secret_key: str
    instance_config_path: str = "config/instance.yaml"
    # Durata sessione in ore (default 30 giorni)
    session_expire_hours: int = 720
    admin_username: str = "admin"
    admin_password: str
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]
    file_storage_path: str = "data/files"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
