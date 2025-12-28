from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = Field(..., validation_alias="DATABASE_URL")
    WEBHOOK_SECRET: Optional[str] = Field(None, validation_alias="WEBHOOK_SECRET")
    LOG_LEVEL: str = Field("INFO", validation_alias="LOG_LEVEL")

    model_config = {"env_file": ".env"}

    @field_validator("DATABASE_URL")
    @classmethod
    def db_must_be_sqlite(cls, v: str):
        if not v.startswith("sqlite:///"):
            raise ValueError("DATABASE_URL must be sqlite:///...")
        return v


settings = Settings()
