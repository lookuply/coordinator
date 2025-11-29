"""Configuration management using Pydantic settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql://lookuply:password@localhost:5432/lookuply"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = "dev-secret-key-change-in-production"

    # Crawling
    max_urls_per_node: int = 10
    crawl_delay_seconds: int = 1
    respect_robots_txt: bool = True

    # Logging
    log_level: str = "INFO"


# Global settings instance
settings = Settings()
