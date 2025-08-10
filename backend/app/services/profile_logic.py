"""Profile & intent parsing / TDEE computation utilities.

Pure functions extracted from the earlier monolithic RAG / chat service so they
can be unit‑tested in isolation and re‑used by multiple services.

Public functions (all side‑effect free):

parse_profile_facts(message: str) -> dict
    Extract any of: sex, age, weight_kg, height_cm, activity_factor from a
    single user message. Missing items are set to None.

rebuild_profile(history: list[dict]) -> dict
    Fold over a chat history (list of {'role': str, 'content': str}) applying
    parse_profile_facts to each user message; later mentions override earlier.

is_tdee_intent(message: str) -> bool
    Lightweight lexical intent detection for TDEE / calorie questions.

detect_recall(message: str) -> str | None
    Detect if the user is asking you to recall a previously provided datum;
    returns the canonical field name or None.

already_asked(message: str, pending: set[str]) -> bool
    Given a candidate assistant message *that you are about to send* (or have
    just sent) and a set of fields you still need, return True if this message
    already asks for ANY of those fields (so you do not re‑ask immediately).

unresolved_tdee(profile: dict) -> list[str]
    Return list of profile field names required for TDEE that are still None.

compute_tdee(profile: dict) -> dict
    Compute BMR + low/high TDEE band. Requires all fields present; raises
    ValueError if any are missing.

format_tdee(result: dict, profile: dict) -> str
    Human readable sentence summarising BMR / TDEE + gentle disclaimer.

Height Parsing Supported Examples:
    5'11"   5' 11   5 ft 11 in   5ft11   5 feet 11 inches
    180 cm  72 in   1.80 m   1.8 m

Imperial inputs converted to metric (cm / kg). Weight supports lb / lbs / kg.

NOTE: These heuristics are intentionally conservative; they should not throw.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
import re

# ================= Constants ==================
RE_GENDER = re.compile(r"\b(male|female|man|woman|boy|girl|m|f)\b", re.I)
RE_AGE = re.compile(r"\b(1[0-9]|[2-8][0-9])\s*(?:yo|y/o|years?|yrs?)?\b", re.I)
RE_WEIGHT = re.compile(r"\b(\d{2,3})\s*(kg|kilograms|lbs|lb|pounds?)\b", re.I)

# Height variants (imperial feet + inches)
RE_HEIGHT_FEET_IN = re.compile(
    r"""
    (?P<feet>\b\d{1,2})  # feet
    \s*(?:ft|foot|feet|['′])\s*  # unit / prime
    (?P<inch>\d{1,2})     # inches
    \s*(?:in|inch|inches|["″])?  # optional inch marker
    \b
    """,
    re.I | re.X,
)
# Compact form like 5'11 or 5′11"
RE_HEIGHT_COMPACT = re.compile(r"\b(?P<feet>\d{1,2})\s*['′]\s*(?P<inch>\d{1,2})(?:[\"″])?\b")
# Form like 5ft11 (no space before inches)
RE_HEIGHT_FT_NO_SPACE = re.compile(r"\b(?P<feet>\d{1,2})\s*(?:ft|')\s*(?P<inch>\d{1,2})\b", re.I)
# Metric
RE_HEIGHT_CM = re.compile(r"\b(\d{2,3})\s*cm\b", re.I)
RE_HEIGHT_METERS = re.compile(r"\b(1\.[3-9]\d?|2\.[0-2]\d?|\d\.\d)\s*m\b", re.I)  # 1.3m - 2.29m etc.
# Inches only
RE_HEIGHT_IN_ONLY = re.compile(r"\b(5\d|6\d|7[0-2])\s*(?:in|inch|inches)\b", re.I)  # plausible adult range

# Activity factor dictionary (Harris-Benedict style multipliers)
ACTIVITY_FACTORS: Dict[str, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "very": 1.725,
    "extra": 1.9,
}

ACTIVE_JOB_WORDS = [
    "produce", "warehouse", "stock", "stocking", "retail", "server", "barista", "nurse", "construction", "lifting boxes",
    "on my feet", "on feet", "walk", "walking"
]
RESISTANCE_TRAINING_WORDS = ["lift", "lifting", "weights", "weight training", "gym", "resistance"]

TDEE_KEYWORDS = ["tdee", "maintenance", "calorie", "calories", "bmr", "burn each day", "daily burn"]
START_TDEE_TRIGGERS = re.compile(r"(what\s+should\s+i\s+start|where\s+do\s+i\s+start|how\s+do\s+i\s+start)", re.I)

RECALL_PATTERNS = {
    "height_cm": re.compile(r"(my\s+height|how\s+tall\s+am\s+i)", re.I),
    "weight_kg": re.compile(r"(my\s+weight|how\s+much\s+do\s+i\s+weigh)", re.I),
    "age": re.compile(r"(my\s+age|how\s+old\s+am\s+i)", re.I),
    "sex": re.compile(r"(my\s+(sex|gender))", re.I),
    "activity_factor": re.compile(r"(my\s+activity|activity\s+level)", re.I),
}

ASK_PATTERNS = {
    "sex": re.compile(r"sex", re.I),
    "age": re.compile(r"age", re.I),
    "weight_kg": re.compile(r"weight", re.I),
    "height_cm": re.compile(r"height", re.I),
    "activity_factor": re.compile(r"activity", re.I),
}

PROFILE_FIELDS = ["sex", "age", "weight_kg", "height_cm", "activity_factor"]

# ================= Internal helpers ==================

def _infer_activity_factor(text: str) -> Optional[float]:
    low = text.lower()
    job_hits = sum(1 for w in ACTIVE_JOB_WORDS if w in low)
    train_hits = sum(1 for w in RESISTANCE_TRAINING_WORDS if w in low)
    # Very light heuristic: if both appear, moderate.
    if job_hits and train_hits:
        return ACTIVITY_FACTORS["moderate"]
    if job_hits:
        if "construction" in low or "warehouse" in low:
            return ACTIVITY_FACTORS["moderate"]
        return ACTIVITY_FACTORS["light"]
    if train_hits:
        if re.search(r"(3|4|5)\s*(x|times)?\s*(a|per)?\s*week", low):
            return ACTIVITY_FACTORS["light"]
        return ACTIVITY_FACTORS["sedentary"]
    return None


def _extract_height_cm(text: str) -> Optional[float]:
    lower = text.lower()
    m = (
        RE_HEIGHT_FEET_IN.search(lower)
        or RE_HEIGHT_COMPACT.search(lower)
        or RE_HEIGHT_FT_NO_SPACE.search(lower)
    )
    if m:
        try:
            feet = float(m.group("feet"))
            inch = float(m.group("inch"))
            if 0 <= inch < 12 and 3 <= feet <= 8:
                return (feet * 12 + inch) * 2.54
        except Exception:  # noqa: BLE001
            pass
    m = RE_HEIGHT_CM.search(lower)
    if m:
        try:
            cm = float(m.group(1))
            if 90 <= cm <= 250:
                return cm
        except Exception:
            pass
    m = RE_HEIGHT_METERS.search(lower)
    if m:
        try:
            meters = float(m.group(1))
            cm = meters * 100
            if 90 <= cm <= 250:
                return cm
        except Exception:
            pass
    m = RE_HEIGHT_IN_ONLY.search(lower)
    if m:
        try:
            inches = float(m.group(1))
            cm = inches * 2.54
            if 90 <= cm <= 250:
                return cm
        except Exception:
            pass
    return None

# ================= Public API ==================

def parse_profile_facts(message: str) -> Dict[str, Optional[Any]]:
    """Parse individual message for profile facts.

    Returns dict with keys: sex, age, weight_kg, height_cm, activity_factor.
    Missing values are None.
    """
    lower = message.lower()
    out: Dict[str, Optional[Any]] = {k: None for k in PROFILE_FIELDS}

    g = RE_GENDER.search(lower)
    if g:
        first = g.group(1).lower()
        out["sex"] = "male" if first[0] == "m" or "man" in first or "boy" in first else "female"

    a = RE_AGE.search(lower)
    if a:
        try:
            age = float(a.group(1))
            out["age"] = age
        except Exception:
            pass

    w = RE_WEIGHT.search(lower)
    if w:
        try:
            val = float(w.group(1))
            unit = w.group(2).lower()
            out["weight_kg"] = val if "kg" in unit else val * 0.4536
        except Exception:
            pass

    h_cm = _extract_height_cm(lower)
    if h_cm is not None:
        out["height_cm"] = h_cm

    # Direct lexical activity factor
    for k, f in ACTIVITY_FACTORS.items():
        if k in lower:
            out["activity_factor"] = f
            break
    if out["activity_factor"] is None:
        inferred = _infer_activity_factor(message)
        if inferred:
            out["activity_factor"] = inferred

    return out


def rebuild_profile(history: List[Dict[str, str]]) -> Dict[str, Optional[Any]]:
    """Aggregate profile state over user messages.

    history: list of {role: 'user'|'assistant'|..., content: str}
    Only user messages contribute new facts. Later facts override earlier ones.
    """
    profile: Dict[str, Optional[Any]] = {k: None for k in PROFILE_FIELDS}
    for turn in history:
        if turn.get("role") != "user":
            continue
        facts = parse_profile_facts(turn.get("content", ""))
        for k, v in facts.items():
            if v is not None:
                profile[k] = v
    return profile


def is_tdee_intent(message: str) -> bool:
    low = message.lower()
    return any(k in low for k in TDEE_KEYWORDS) or bool(START_TDEE_TRIGGERS.search(low))


def detect_recall(message: str) -> Optional[str]:
    lower = message.lower()
    for field, pat in RECALL_PATTERNS.items():
        if pat.search(lower):
            return field
    return None


def already_asked(message: str, pending: Set[str]) -> bool:
    """Return True if assistant message already asks for ANY pending field.

    You would typically use this before deciding to repeat a question.
    """
    low = message.lower()
    for field in pending:
        pat = ASK_PATTERNS.get(field)
        if pat and pat.search(low) and "?" in low:
            return True
    return False


def unresolved_tdee(profile: Dict[str, Optional[Any]]) -> List[str]:
    """Return list of missing required fields for TDEE.

    Required: sex, age, weight_kg, height_cm, activity_factor
    """
    return [f for f in PROFILE_FIELDS if profile.get(f) in (None, "", 0)]


def compute_tdee(profile: Dict[str, Optional[Any]]) -> Dict[str, int]:
    """Compute BMR and TDEE band.

    Returns dict with keys: bmr, tdee_low, tdee_high.
    Raises ValueError if any required field missing.
    """
    missing = unresolved_tdee(profile)
    if missing:
        raise ValueError(f"Missing fields for TDEE: {missing}")
    sex = str(profile["sex"])  # type: ignore
    weight = float(profile["weight_kg"])  # type: ignore
    height = float(profile["height_cm"])  # type: ignore
    age = float(profile["age"])  # type: ignore
    act = float(profile["activity_factor"])  # type: ignore
    if sex.startswith("m"):
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    tdee = bmr * act
    return {
        "bmr": int(round(bmr)),
        "tdee_low": int(round(tdee * 0.95)),
        "tdee_high": int(round(tdee * 1.05)),
    }


def format_tdee(result: Dict[str, int], profile: Dict[str, Optional[Any]]) -> str:
    """Format a user‑facing BMR/TDEE response string.

    Adds a simple BMI plausibility note (non‑medical) if extreme.
    """
    bmr = result["bmr"]
    low = result["tdee_low"]
    high = result["tdee_high"]
    bmi_note = ""
    try:
        weight = float(profile["weight_kg"])  # type: ignore
        height_m = float(profile["height_cm"]) / 100.0  # type: ignore
        bmi = weight / (height_m ** 2)
        if bmi < 16 or bmi > 40:
            bmi_note = " If you can, talk to a health professional."
    except Exception:
        pass
    return (
        f"Your body at rest uses about {bmr} calories (BMR). "
        f"Daily burn about {low}-{high} calories (TDEE). "
        f"This is only a rough guess, not medical advice.{bmi_note}"
    )


__all__ = [
    "parse_profile_facts",
    "rebuild_profile",
    "is_tdee_intent",
    "detect_recall",
    "already_asked",
    "unresolved_tdee",
    "compute_tdee",
    "format_tdee",
]
