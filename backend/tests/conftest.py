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
    monkeypatch.setattr(rag_service, "_model_available", lambda: False)
    yield
    monkeypatch.setattr(rag_service, "_model_available", lambda: True, raising=False)


@pytest.fixture
def mock_generate(monkeypatch: pytest.MonkeyPatch):
    """Mock the LLM generation path with a fixed return value.

    Ensure model path is taken by faking availability.
    Returns a function allowing caller to set the desired reply.
    """
    monkeypatch.setattr(rag_service, "_model_available", lambda: True)
    state = {"reply": "Fixed reply"}

    def _fake(prompt: str) -> str:  # noqa: D401
        return state["reply"]

    monkeypatch.setattr(rag_service, "_generate_response", _fake)

    def setter(value: str) -> None:
        state["reply"] = value

    return setter


@pytest.fixture
def openrouter_mock(monkeypatch: pytest.MonkeyPatch):
    """Monkeypatch OpenRouter client call to a deterministic mock response."""
    from app.services import openrouter_client

    monkeypatch.setattr(
        openrouter_client,
        "generate_response",
        lambda prompt, **_: "[mocked LLM]",
    )
    return openrouter_client.generate_response
