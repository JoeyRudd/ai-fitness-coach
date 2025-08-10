"""Gemini generative AI client helper.

Provides a single public function ``generate_response(prompt: str) -> str`` that
wraps the Google Generative AI (Gemini) SDK while adding:

- Lazy, module‑level singleton style initialization (first call only)
- Model selection via ``GEMINI_MODEL`` env var (default: ``gemini-1.5-flash``)
- Graceful fallback when ``GEMINI_API_KEY`` is missing or unusable, returning a
  deterministic string ``"[LLM unavailable: fallback]"`` so callers can rely on
  consistent behaviour in offline / test environments.
- Lightweight safety / hygiene layer:
  * Truncates incoming prompt to a hard limit (6000 characters)
  * Strips / neutralises a small list of potentially dangerous or prompt‑leaking
    tokens (markdown fences, HTML script tags, role prefixes, etc.)
- Defensive exception handling so any SDK error also yields the fallback string
  rather than propagating.

This module intentionally keeps a minimal surface to simplify testing and
mocking. For more advanced usage (multi‑turn chats, tool calling, etc.), extend
or replace this wrapper.
"""
from __future__ import annotations

from typing import Final, List, Optional
import logging
import os

try:  # Import guarded so environments without the package still work gracefully.
    import google.generativeai as genai  # type: ignore
except Exception:  # pragma: no cover - only hit when package is absent.
    genai = None  # type: ignore

logger = logging.getLogger(__name__)

_FALLBACK_RESPONSE: Final[str] = "[LLM unavailable: fallback]"
_MAX_PROMPT_CHARS: Final[int] = 6000
_DANGEROUS_TOKENS: Final[List[str]] = [
    "```",  # markdown fences
    "<script", "</script>",
    "system:", "user:", "assistant:",  # role style prefixes
    "@@", "{{", "}}",  # template delimiters sometimes abused
]

_model: Optional["genai.GenerativeModel"] = None  # type: ignore[name-defined]
_model_name: str = ""
_initialized: bool = False


def _init_client() -> None:
    """Initialise the Gemini client lazily.

    If the API key is missing, we mark as initialized but without a model so
    subsequent calls short‑circuit quickly.
    """
    global _model, _model_name, _initialized
    if _initialized:
        return
    _initialized = True  # Mark early to avoid races / recursion.

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.info("GEMINI_API_KEY missing; Gemini client disabled, using fallback.")
        return

    if genai is None:  # Library not present.
        logger.warning("google-generativeai package not available; using fallback.")
        return

    try:
        genai.configure(api_key=api_key)
        _model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip() or "gemini-1.5-flash"
        _model = genai.GenerativeModel(_model_name)  # type: ignore[attr-defined]
        logger.debug("Gemini model '%s' initialized successfully.", _model_name)
    except Exception as exc:  # pragma: no cover - network / SDK specific
        logger.error("Failed to initialize Gemini client: %s", exc)
        _model = None


def _sanitize_prompt(prompt: str) -> str:
    """Apply simple size + token scrubbing to the prompt.

    This is NOT a comprehensive security filter—just a minimal defensive step.
    """
    truncated = prompt[:_MAX_PROMPT_CHARS]
    cleaned = truncated
    for token in _DANGEROUS_TOKENS:
        cleaned = cleaned.replace(token, " ")
    return cleaned.strip()


def generate_response(prompt: str) -> str:
    """Generate a model response for the provided prompt.

    Behaviour:
    - Returns a deterministic fallback string when the model / key is
      unavailable or any exception occurs.
    - Sanitizes and truncates the prompt prior to sending to the API.

    Parameters
    ----------
    prompt: str
        The raw user prompt / input text.

    Returns
    -------
    str
        Model text output or fallback string.
    """
    if not _initialized:
        _init_client()

    if _model is None:
        return _FALLBACK_RESPONSE

    safe_prompt = _sanitize_prompt(prompt)
    if not safe_prompt:
        return _FALLBACK_RESPONSE

    try:
        # For the flash model, a single-turn generate_content is sufficient.
        response = _model.generate_content(safe_prompt)  # type: ignore[operator]
        # The SDK typically exposes .text; fall back to joining candidates if needed.
        text: Optional[str] = getattr(response, "text", None)
        if text and text.strip():
            return text.strip()
        # Fallback path: attempt to assemble from candidates / parts.
        candidates = getattr(response, "candidates", None)
        if candidates:
            parts: list[str] = []
            for cand in candidates:  # type: ignore[assignment]
                content = getattr(cand, "content", None)
                if content and getattr(content, "parts", None):
                    for part in content.parts:  # type: ignore[assignment]
                        part_text = getattr(part, "text", "")
                        if part_text:
                            parts.append(part_text)
            if parts:
                return "\n".join(p.strip() for p in parts if p.strip())
        return _FALLBACK_RESPONSE
    except Exception as exc:  # pragma: no cover - network / SDK errors
        logger.error("Gemini generate_content error: %s", exc)
        return _FALLBACK_RESPONSE


__all__ = ["generate_response"]
