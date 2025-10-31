from functools import lru_cache
from pathlib import Path

try:
    from pydantic_settings import BaseSettings
except ImportError:  # fallback for environments without pydantic-settings
    from pydantic import BaseSettings  # type: ignore
from pydantic import Field
from typing import List

class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env.

    You can override any field via environment variable with the upper‑case
    field name, e.g. GEMINI_API_KEY, GEMINI_MODEL_NAME.
    """

    # Empty default so missing key triggers clean fallback (no invalid key attempts)
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    # Default to a widely available Gemini 2.5 model
    gemini_model_name: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL_NAME")
    # OpenRouter config
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="deepseek/deepseek-chat", alias="OPENROUTER_MODEL")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL")
    openrouter_site_url: str = Field(default="http://localhost:5173", alias="OPENROUTER_SITE_URL")
    openrouter_app_title: str = Field(default="AI Fitness Coach", alias="OPENROUTER_APP_TITLE")
    allowed_origins: str = Field(default="http://localhost:5173", alias="ALLOWED_ORIGINS")  # comma-separated
    knowledge_base_path: str = Field(default="knowledge_base", alias="KNOWLEDGE_BASE_PATH")
    max_retrieval_chunks: int = Field(default=4, alias="MAX_RETRIEVAL_CHUNKS")
    embedding_model_name: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL_NAME")

    class Config:
        # Allow either project root .env or backend/.env (first found wins)
        env_file = (".env", "backend/.env")
        case_sensitive = False

    @property
    def allowed_origins_list(self) -> List[str]:  # derived helper for CORS
        return [o.strip() for o in self.allowed_origins.split(',') if o.strip()]

    @property
    def knowledge_base_path_resolved(self) -> str:
        """Resolve knowledge_base_path against known roots when relative.

        Resolution order for relative paths:
        1) repo root / knowledge_base
        2) backend dir / knowledge_base
        3) current working directory / knowledge_base
        Returns the first existing directory; else returns repo-root candidate.
        """
        p = Path(self.knowledge_base_path)
        if p.is_absolute():
            return str(p)
        here = Path(__file__).resolve()
        # parents[0]=core, [1]=app, [2]=backend, [3]=repo root
        repo_root = here.parents[3] if len(here.parents) >= 4 else here.parent
        backend_dir = here.parents[2] if len(here.parents) >= 3 else here.parent
        candidates = [
            (repo_root / p),
            (backend_dir / p),
            (Path.cwd() / p),
        ]
        for c in candidates:
            try:
                if c.exists() and c.is_dir():
                    return str(c)
            except Exception:
                # In case of permission or race conditions, keep trying others
                pass
        return str(candidates[0])

@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]

settings = get_settings()
