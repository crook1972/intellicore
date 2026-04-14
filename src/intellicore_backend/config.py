from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "IntelliCore MVP"
    db_url: str = "sqlite:///./intellicore.db"
    bacnet_ip: str = "127.0.0.1/24"
    bacnet_poll_limit: int = 5
    live_refresh_seconds: int = 5

    modbus_host: str = "127.0.0.1"
    modbus_port: int = 502
    modbus_unit_id: int = 1
    modbus_start_address: int = 0
    modbus_register_count: int = 10

    model_config = SettingsConfigDict(env_prefix="INTELLICORE_", extra="ignore")


settings = Settings()
