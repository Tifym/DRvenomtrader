"""
Dr. Venom Trader - Application Configuration
Centralizes all settings from environment variables.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- General ---
    app_name: str = "Dr. Venom Trader"
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="info", alias="LOG_LEVEL")
    secret_key: str = Field(default="changeme", alias="SECRET_KEY")

    # --- Server ---
    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")

    # --- Database ---
    database_url: str = Field(
        default="postgresql+asyncpg://venom:venom@postgres:5432/drvenomtrader",
        alias="DATABASE_URL",
    )

    # --- Redis ---
    redis_url: str = Field(
        default="redis://redis:6379/0",
        alias="REDIS_URL",
    )

    # --- Exchange APIs ---
    binance_api_key: str = Field(default="", alias="BINANCE_API_KEY")
    binance_api_secret: str = Field(default="", alias="BINANCE_API_SECRET")
    bybit_api_key: str = Field(default="", alias="BYBIT_API_KEY")
    bybit_api_secret: str = Field(default="", alias="BYBIT_API_SECRET")

    # --- CoinGlass ---
    coinglass_api_key: str = Field(default="", alias="COINGLASS_API_KEY")

    # --- Alerts ---
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")
    discord_webhook_url: str = Field(default="", alias="DISCORD_WEBHOOK_URL")

    # --- Trading Config ---
    default_symbols: List[str] = ["BTCUSDT", "ETHUSDT"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore",
    }


# Singleton instance
settings = Settings()
