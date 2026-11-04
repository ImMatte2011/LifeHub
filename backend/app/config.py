from pydantic_settings import BaseSettings, SettingsConfigDict


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
    admin_password: str = "admin"
    debug: bool = False


settings = Settings()
