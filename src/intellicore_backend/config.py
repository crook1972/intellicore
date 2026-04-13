from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "IntelliCore MVP"
    db_url: str = "sqlite:///./intellicore.db"
    bacnet_ip: str = "127.0.0.1/24"
    bacnet_poll_limit: int = 5

    model_config = SettingsConfigDict(env_prefix="INTELLICORE_", extra="ignore")


settings = Settings()
