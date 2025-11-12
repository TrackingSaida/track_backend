from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGO: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 dias

    class Config:
        env_file = ".env"

@lru_cache
def get_settings():
    return Settings()
