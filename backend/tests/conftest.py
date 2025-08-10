import pytest
from fastapi.testclient import TestClient

from app.main import app  # FastAPI instance
from app.services.rag_service import rag_service


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def force_fallback(monkeypatch: pytest.MonkeyPatch):
    """Force the service into deterministic fallback (no model)."""
    orig_model = getattr(rag_service, "_model", None)
    monkeypatch.setattr(rag_service, "_model", None)
    yield
    monkeypatch.setattr(rag_service, "_model", orig_model, raising=False)


@pytest.fixture
def mock_generate(monkeypatch: pytest.MonkeyPatch):
    """Mock the LLM generation path with a fixed return value.

    Sets a sentinel _model (truthy) so normal general intent path is taken.
    Returns a function allowing caller to set the desired reply.
    """
    sentinel_model = object()
    monkeypatch.setattr(rag_service, "_model", sentinel_model)
    state = {"reply": "Fixed reply"}

    def _fake(prompt: str) -> str:  # noqa: D401
        return state["reply"]

    monkeypatch.setattr(rag_service, "_generate_response", _fake)

    def setter(value: str) -> None:
        state["reply"] = value

    return setter
