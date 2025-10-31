"""Application package for the AI Fitness Coach backend."""

# Expose FastAPI instance for convenience imports in tests and elsewhere
try:
    from .main import app  # noqa: F401
except Exception:
    # Avoid import-time failures during tooling that scans modules
    pass


