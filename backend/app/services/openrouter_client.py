"""OpenRouter client helper for text generation and TDEE extraction.

Provides:
- generate_response(prompt: str, *, max_tokens=500, temperature=0.55) -> str
- extract_tdee_from_text(user_text: str) -> dict

Uses OpenAI-compatible chat completions endpoint via OpenRouter.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_FALLBACK = "[LLM unavailable: fallback]"


def _headers() -> Dict[str, str]:
    hdrs = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        # Recommended headers for OpenRouter
        "HTTP-Referer": settings.openrouter_site_url,
        "X-Title": settings.openrouter_app_title,
    }
    return hdrs


def _post_chat(messages: List[Dict[str, str]], *, max_tokens: int, temperature: float) -> Optional[Dict[str, Any]]:
    if not settings.openrouter_api_key:
        logger.info("OPENROUTER_API_KEY missing; OpenRouter client disabled")
        return None
    url = f"{settings.openrouter_base_url.rstrip('/')}/chat/completions"
    payload: Dict[str, Any] = {
        "model": settings.openrouter_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=_headers(), json=payload)
            if resp.status_code >= 400:
                logger.warning("OpenRouter error %s: %s", resp.status_code, resp.text[:300])
                return None
            return resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.error("OpenRouter request failed: %s", exc)
        return None


def _extract_text(resp_json: Dict[str, Any]) -> str:
    try:
        choices = resp_json.get("choices") or []
        if not choices:
            return _FALLBACK
        msg = (choices[0] or {}).get("message") or {}
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    except Exception:  # noqa: BLE001
        pass
    return _FALLBACK


def generate_response(prompt: str, *, max_tokens: int = 500, temperature: float = 0.55) -> str:
    messages = [
        {"role": "system", "content": "You are a friendly, safety-first fitness coach for beginners. Keep answers concise and practical."},
        {"role": "user", "content": prompt},
    ]
    data = _post_chat(messages, max_tokens=max_tokens, temperature=temperature)
    if not data:
        return _FALLBACK
    return _extract_text(data)


def extract_tdee_from_text(user_text: str) -> Dict[str, Any]:
    """Instruct the model to return strict JSON for TDEE extraction."""
    schema_desc = (
        "Respond ONLY in JSON with keys: sex, age, weight_kg, height_cm, activity_factor, bmr, tdee, explanation. "
        "Set missing values to null. No extra text."
    )
    prompt = (
        f"You extract user profile and energy needs. {schema_desc}\n\n"
        "Rules: Map activity to numeric factor: sedentary 1.2, light 1.375, moderate 1.55, very 1.725, extra 1.9.\n"
        "Use Mifflin-St Jeor for BMR and multiply by activity factor for TDEE.\n"
        f"User chat history: '''{user_text}'''\n"
    )
    messages = [
        {"role": "system", "content": "Return JSON only. Do not include any text outside of JSON."},
        {"role": "user", "content": prompt},
    ]
    data = _post_chat(messages, max_tokens=350, temperature=0.2)
    if not data:
        return {"error": "OpenRouter unavailable", "raw_response": None}
    text = _extract_text(data)
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
    except Exception:  # noqa: BLE001
        pass
    return {"error": "Could not parse JSON", "raw_response": text}


__all__ = ["generate_response", "extract_tdee_from_text"]


