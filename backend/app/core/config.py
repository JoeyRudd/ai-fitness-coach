from functools import lru_cache

try:
    from pydantic_settings import BaseSettings
except ImportError:  # fallback for environments without pydantic-settings
    from pydantic import BaseSettings  # type: ignore
from pydantic import Field

class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env.

    You can override any field via environment variable with the upper‑case
    field name, e.g. GEMINI_API_KEY, GEMINI_MODEL_NAME.
    """

    gemini_api_key: str = Field(default="your_secret_api_key_here", alias="GEMINI_API_KEY")
    gemini_model_name: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL_NAME")

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]

settings = get_settings()
