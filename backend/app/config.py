from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./bussola.db"
    secret_key: str = "dev-only-change-in-production-please"
    access_token_expire_minutes: int = 60 * 8
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    anthropic_api_key: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v):
        # Permite CORS_ORIGINS=https://a.com,https://b.com via env
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    class Config:
        env_file = ".env"


settings = Settings()
