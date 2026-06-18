from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "政务好差评闭环督办系统"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_PORT: int = 8000

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "review_supervision"

    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    TIMEZONE: str = "Asia/Shanghai"

    SUPERVISE_TIMEOUT_HOURS: int = 24
    FEEDBACK_TIMEOUT_HOURS: int = 72
    REVIEW_TIMEOUT_HOURS: int = 120

    URGENT_UPGRADE_HOURS: int = 6
    MAJOR_UPGRADE_HOURS: int = 12

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def SQLITE_URL(self) -> str:
        return "sqlite:///./review_supervision.db"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
