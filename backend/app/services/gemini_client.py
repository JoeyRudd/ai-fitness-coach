"""Gemini generative AI client helper.

Provides a single public function ``generate_response(prompt: str) -> str`` that
wraps the Google Generative AI (Gemini) SDK while adding:

- Lazy, module-level singleton style initialization (first call only)
- Model selection via ``GEMINI_MODEL`` env var (default: ``gemini-1.5-flash``)
- Graceful fallback when ``GEMINI_API_KEY`` is missing or unusable
- Lightweight safety / hygiene layer
- Defensive exception handling so any SDK error yields a fallback string
"""

from __future__ import annotations
from typing import Final, List, Optional
import logging
import os
import json

    try:  # Import guarded so environments without the package still work gracefully.
    import google.generativeai as genai  # type: ignore
except Exception:  # pragma: no cover
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
    """Initialise the Gemini client lazily."""
    global _model, _model_name, _initialized
    if _initialized:
        return
    _initialized = True

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.info("GEMINI_API_KEY missing; Gemini client disabled.")
        return

    if genai is None:
        logger.warning("google-generativeai package not available.")
        return

    try:
        genai.configure(api_key=api_key)
        # Prefer GEMINI_MODEL_NAME, then GEMINI_MODEL, else use a broadly supported default
        configured_name = (
            os.getenv("GEMINI_MODEL_NAME", "").strip()
            or os.getenv("GEMINI_MODEL", "").strip()
        )
        # Default and fallbacks prioritize Gemini 2.5 family (1.5 is deprecated)
        candidate_names = [
            configured_name if configured_name else "gemini-2.5-flash",
            # Fallbacks in case the primary is not available in the deployed API version
            "gemini-2.5-flash-lite",
            "gemini-2.5-pro",
            # As last resorts, try older families that may still be present
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]

        last_exc: Exception | None = None
        for name in candidate_names:
            try:
                if not name:
                    continue
                model = genai.GenerativeModel(name)  # type: ignore[attr-defined]
                # quick no-op call to verify the model exists and supports generateContent
                # Use a minimal prompt to avoid latency; failures will raise
                _ = model.generate_content("ping")
                _model = model
                _model_name = name
                logger.info("Gemini model '%s' initialized.", _model_name)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                logger.warning("Gemini model '%s' not usable: %s", name, exc)

        if _model is None:
            if last_exc is not None:
                logger.error("Failed to initialize Gemini client after fallbacks: %s", last_exc)
            else:
                logger.error("Failed to initialize Gemini client: unknown error")
    except Exception as exc:
        logger.error("Failed to initialize Gemini client: %s", exc)
        _model = None


def _sanitize_prompt(prompt: str) -> str:
    """Apply size limit + minimal token scrubbing."""
    truncated = prompt[:_MAX_PROMPT_CHARS]
    cleaned = truncated
    for token in _DANGEROUS_TOKENS:
        cleaned = cleaned.replace(token, " ")
    return cleaned.strip()


def generate_response(prompt: str) -> str:
    """Generate a Gemini model response for the provided prompt."""
    if not _initialized:
        _init_client()
    if _model is None:
        return _FALLBACK_RESPONSE

    safe_prompt = _sanitize_prompt(prompt)
    try:
        # Optional safety override via env flag (BLOCK_NONE lowers blocking; use responsibly)
        safety_override = os.getenv("GEMINI_SAFETY_OVERRIDE", "false").lower() in {"1","true","yes"}
        safety_settings = None
        if safety_override and genai is not None:
            safety_settings = [
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUAL", "threshold": "BLOCK_NONE"},
            ]

        response = _model.generate_content(safe_prompt, safety_settings=safety_settings)  # type: ignore
        # Prefer robust extraction over response.text quick accessor
        try:
            candidates = getattr(response, "candidates", []) or []
            if candidates:
                # Extract text from parts only; never call response.text
                text_chunks: List[str] = []
                content_obj = getattr(candidates[0], "content", None)
                parts_list = getattr(content_obj, "parts", []) if content_obj else []
                for part in parts_list:
                    text_val = getattr(part, "text", None)
                    if isinstance(text_val, str) and text_val.strip():
                        text_chunks.append(text_val.strip())
                if text_chunks:
                    return "\n".join(text_chunks)

                # If no text parts, examine finish_reason for helpful messaging
                finish_reason = getattr(candidates[0], "finish_reason", None)
                logger.warning(
                    "Gemini returned no text (finish_reason=%s, model=%s).", finish_reason, _model_name
                )
                if finish_reason in (2, "SAFETY"):
                    # One soft retry with safer instructions and lower temperature
                    softened = (
                        "Provide general fitness education only. Avoid medical claims, diagnoses, supplements, or unsafe instructions. "
                        "Keep it practical and safe for beginners.\n\n" + safe_prompt
                    )
                    try:
                        retry_resp = _model.generate_content(
                            softened,
                            safety_settings=safety_settings,  # honor override if set
                            generation_config=genai.types.GenerationConfig(temperature=0.2, max_output_tokens=220) if genai else None,  # type: ignore
                        )
                        retry_candidates = getattr(retry_resp, "candidates", []) or []
                        if retry_candidates:
                            content_obj2 = getattr(retry_candidates[0], "content", None)
                            parts2 = getattr(content_obj2, "parts", []) if content_obj2 else []
                            retry_chunks: List[str] = []
                            for p in parts2:
                                t = getattr(p, "text", None)
                                if isinstance(t, str) and t.strip():
                                    retry_chunks.append(t.strip())
                            if retry_chunks:
                                return "\n".join(retry_chunks)
                    except Exception:
                        pass
                    return "I couldn't answer that due to safety filters. Please rephrase or ask something else."
        except Exception:
            # Ignore extraction errors and fall through to generic handling
            pass

        return _FALLBACK_RESPONSE
    except Exception as exc:
        logger.error("Gemini generation failed for model '%s': %s", _model_name, exc)
        return _FALLBACK_RESPONSE


def extract_tdee_from_text(user_text: str) -> dict:
    """
    Use Gemini to extract TDEE and profile info from user input.
    Returns a dict with keys: sex, age, weight_kg, height_cm,
    activity_factor, bmr, tdee, explanation.
    Missing values are null.
    """
    prompt = f"""
You are a fitness and nutrition assistant. Extract the following from the user's combined chat history:
- sex (male/female)
- age (years)
- weight (kg)
- height (cm)
- activity level (choose one: sedentary, light, moderate, very, extra)
- If the user describes their activity (e.g., 'I exercise 4 times a week', 'I am active', 'I walk daily'), map it to the closest standard level and set the corresponding activity_factor:
    - sedentary: 1.2
    - light: 1.375
    - moderate: 1.55
    - very: 1.725
    - extra: 1.9
Then estimate their TDEE (Total Daily Energy Expenditure) and BMR (Basal Metabolic Rate) using the Mifflin-St Jeor equation and the activity factor.
Respond ONLY in JSON with these keys: sex, age, weight_kg, height_cm, activity_factor, bmr, tdee, explanation.
If any value is missing, set it to null.
Example:
{{"sex": "male", "age": 30, "weight_kg": 80, "height_cm": 180, "activity_factor": 1.55, "bmr": 1750, "tdee": 2712, "explanation": "..."}}

User chat history: '''{user_text}'''
"""
    response = generate_response(prompt)
    try:
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = response[start:end + 1]
            return json.loads(json_str)
    except Exception:
        pass
    return {"error": "Could not extract TDEE info from Gemini response.", "raw_response": response}


__all__ = ["generate_response", "extract_tdee_from_text"]