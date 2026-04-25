from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "order-service"
    environment: str = "local"
    log_level: str = "INFO"

    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:9092"
    order_created_topic: str = "orders.created"

    jwt_secret_key: str = "local-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "order-service"
    jwt_audience: str = "order-service-api"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings() # type: ignore[call-arg]