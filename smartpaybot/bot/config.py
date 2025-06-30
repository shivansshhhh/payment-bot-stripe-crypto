# bot/config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    DOMAIN_URL: str
    ADMIN_ID: int

    class Config:
        env_file = ".env"

settings = Settings()
