"""RAGService encapsulates the logic previously embedded in main.py.

While the original provided snippet described a /chat endpoint performing RAG over a knowledge base
and calling Gemini, the actual monolithic file implements a conversational calorie/TDEE assistant.
We keep all that business logic here without changing functionality, exposing a clean method
get_ai_response(history) that returns the HistoryChatResponse fields.
"""
from __future__ import annotations

import logging, os, re
from typing import List, Dict, Any, Optional, Tuple

import google.generativeai as genai
from fastapi import HTTPException

from app.core.config import settings
# Make model_config import optional since we removed ML dependencies
try:
    from app.core.model_config import MODEL_CONFIG
except ImportError:
    MODEL_CONFIG = None
from app.models.chat import (
    ChatMessage,
    HistoryChatResponse,
    Profile,
)
from app.services.rag_index import RAGIndex

logger = logging.getLogger("fitness_coach")

# ====================== Constants / Persona =================
APP_PERSONA = (
    "You are a friendly, encouraging, safety‑first fitness coach for true beginners (often mid‑40s). "
    "Sound natural and human. Warm, calm, optimistic. Use contractions and plain words. "
    "Keep messages brief (1–3 short paragraphs). No bullet lists unless the user asks. "
    "Avoid medical claims or diagnoses."
)
GEMINI_MODEL_NAME = settings.gemini_model_name
# Prompt instruction block appended after persona & optional context
ANTI_HALLUCINATION_RULES = (
    "If something isn’t in the context or user message, say what you don’t know briefly, "
    "ask one short clarifying question, or offer a safe, general guideline with a clear caveat. "
    "Never invent numbers or facts. Be supportive without sounding robotic."
)

# ====================== Regex & Patterns ====================
RE_GENDER = re.compile(r"\b(male|female|man|woman|boy|girl|m|f)\b", re.I)
RE_AGE = re.compile(r"\b(\d{2})\s*(?:yo|y/o|years?|yrs?)?\b", re.I)
RE_WEIGHT = re.compile(r"\b(\d{2,3})\s*(kg|kilograms|lbs|lb|pounds?)\b", re.I)
RE_HEIGHT_FT_IN = re.compile(r"(\d)\s*[’']\s*(\d{1,2})")  # allow optional space: matches 5'6 or 5 '6
RE_HEIGHT_FT_IN_WORDS = re.compile(r"(\d)\s*(?:ft|foot|feet)\s*(\d{1,2})\s*(?:in|inch|inches)?", re.I)
EXTRA_HEIGHT_FT_IN_LOOSE = re.compile(r"(\d)\s+(\d{1,2})\b")  # fallback like '5 6'
RE_HEIGHT_CM = re.compile(r"\b(\d{2,3})\s*cm\b", re.I)
RE_HEIGHT_IN = re.compile(r"\b(\d{2})\s*(?:in|inch|inches)\b", re.I)

# Cliché safety phrases should be avoided unless user asks about safety/pain
SAFETY_TRIGGER = re.compile(r"(safe|safety|injur(?:y|ies)|hurt|pain|form|medical|doctor|physician|therap|rehab)", re.I)
CLICHE_PATTERNS = [
    re.compile(r"\blisten to your body\b", re.I),
    re.compile(r"\bif (you )?feel( any)? pain[^.?!]*\bstop\b", re.I),
    re.compile(r"\bstop if (you )?feel pain\b", re.I),
    re.compile(r"\btalk to (a|your) doctor\b", re.I),
]

ACTIVITY_FACTORS: Dict[str,float] = {
    'sedentary': 1.2,
    'light': 1.375,
    'moderate': 1.55,
    'very': 1.725,
    'extra': 1.9
}

ACTIVE_JOB_WORDS = [
    'produce', 'warehouse', 'stock', 'stocking', 'retail', 'server', 'barista', 'nurse', 'construction', 'lifting boxes',
    'on my feet', 'on feet', 'walk', 'walking'
]
RESISTANCE_TRAINING_WORDS = ['lift', 'lifting', 'weights', 'weight training', 'gym', 'resistance']

TDEE_KEYWORDS = ["tdee", "maintenance", "calorie", "calories", "bmr", "burn each day", "daily burn"]
START_TDEE_TRIGGERS = re.compile(r"(what\s+should\s+i\s+start|where\s+do\s+i\s+start|how\s+do\s+i\s+start)", re.I)

RECALL_PATTERNS = {
    'height_cm': re.compile(r"(my\s+height|how\s+tall\s+am\s+i)", re.I),
    'weight_kg': re.compile(r"(my\s+weight|how\s+much\s+do\s+i\s+weigh)", re.I),
    'age': re.compile(r"(my\s+age|how\s+old\s+am\s+i)", re.I),
    'sex': re.compile(r"(my\s+(sex|biological\s+sex))", re.I),
    'activity_factor': re.compile(r"(my\s+activity|activity\s+level)", re.I)
}

ASK_PATTERNS = {
    'sex': re.compile(r"sex", re.I),
    'age': re.compile(r"age", re.I),
    'weight_kg': re.compile(r"weight", re.I),
    'height_cm': re.compile(r"height", re.I),
    'activity_factor': re.compile(r"activity", re.I)
}
FIELD_ORDER = ['sex','age','weight_kg','height_cm','activity_factor']
FIELD_HUMAN = {
    'sex': 'biological sex (male or female)',
    'age': 'age',
    'weight_kg': 'weight',
    'height_cm': 'height',
    'activity_factor': 'activity level (sedentary, light, moderate, very, extra)'
}

# ====================== Service Class =======================
class RAGService:
    def __init__(self) -> None:
        self._model = None
        self._configure_genai()
        # RAG index load - handle missing ML dependencies gracefully
        try:
            self._rag_index = RAGIndex()
            kb_path = getattr(settings, 'knowledge_base_path_resolved', settings.knowledge_base_path)
            logger.info("Using knowledge base path: %s", kb_path)
            self._rag_index.load(kb_path)
            logger.info("RAG knowledge base loaded for prompt grounding: %d docs", len(getattr(self._rag_index, '_docs', [])))
            # Eagerly build the index on startup
            if self._rag_index and self._rag_index._docs:
                self._rag_index.build()
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to init RAG index (likely missing ML deps): %s", e)
            self._rag_index = None

    # ----- Model init -----
    def _configure_genai(self) -> None:
        api_key = settings.gemini_api_key
        if not api_key:
            logger.error("GEMINI_API_KEY missing")
            return
        try:
            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel(GEMINI_MODEL_NAME)
            logger.info("Gemini model initialized")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Gemini init failed: {e}")

    # ================== Public API ==================

    def get_ai_response(self, history: List[ChatMessage]) -> HistoryChatResponse:
        # Match original behavior of /chat2 endpoint.
        user_turns = [t for t in history if t.role == 'user']
        empty_profile_dict = {'sex': None,'age': None,'weight_kg': None,'height_cm': None,'activity_factor': None}
        if not user_turns:
            return HistoryChatResponse(response="Please send a message.", profile=empty_profile_dict, tdee=None, missing=FIELD_ORDER, asked_this_intent=[], intent='none')
        last_user = user_turns[-1].content
        profile = self._rebuild_profile(history)
        missing = self._profile_missing(profile)

        # Detect intent from last user message

        # Gather all user messages for Gemini context
        user_history_text = '\n'.join([t.content for t in user_turns])

        if self._is_tdee_intent(last_user):
            intent = 'tdee'
        else:
            intent = 'general'

        recall_field = self._detect_recall(last_user)
        if recall_field:
            resp_text = self._handle_recall(recall_field, profile)

        if intent == 'tdee':
            # Try Gemini-based TDEE extraction first, using all user messages as context
            gemini_result = None
            try:
                from app.services.gemini_client import extract_tdee_from_text
                gemini_result = extract_tdee_from_text(user_history_text)
            except Exception as e:
                logger.warning(f"Gemini TDEE extraction failed: {e}")

            # Merge Gemini result with existing profile
            merged_profile = dict(profile)
            if isinstance(gemini_result, dict):
                for k in ['sex','age','weight_kg','height_cm','activity_factor']:
                    v = gemini_result.get(k)
                    if v is not None:
                        merged_profile[k] = v

            # Check if all required fields are present after merging
            merged_missing = [k for k in FIELD_ORDER if not merged_profile.get(k)]
            if not merged_missing:
                # Use Gemini's TDEE if available, else fallback to manual
                tdee_val = None
                bmr_val = None
                if gemini_result and gemini_result.get('tdee') and gemini_result.get('bmr'):
                    tdee_val = gemini_result['tdee']
                    bmr_val = gemini_result['bmr']
                else:
                    bmr_val, tdee_val = self._compute_tdee(
                        merged_profile['sex'], merged_profile['weight_kg'], merged_profile['height_cm'], merged_profile['age'], merged_profile['activity_factor']
                    )
                low = int(tdee_val*0.95); high = int(tdee_val*1.05)
                resp_text = gemini_result.get('explanation') if gemini_result and gemini_result.get('explanation') else self._format_tdee(merged_profile, bmr_val, tdee_val)
                tdee_obj = {'bmr': int(bmr_val), 'tdee': int(tdee_val), 'range': [low, high]}
                return HistoryChatResponse(response=resp_text, profile=merged_profile, tdee=tdee_obj, missing=[], asked_this_intent=[], intent='tdee')

            # If still missing fields, prompt for the next one
            ask_field: Optional[str] = None
            for f in FIELD_ORDER:
                if f in merged_missing and not self._already_asked(f, history):
                    ask_field = f
                    break
            if ask_field:
                human = FIELD_HUMAN[ask_field]
                resp_text = f"Can you tell me your {human}?" if ask_field != 'activity_factor' else "What is your activity level? (sedentary, light, moderate, very, extra)"
                return HistoryChatResponse(response=resp_text, profile=merged_profile, tdee=None, missing=merged_missing, asked_this_intent=[ask_field], intent='tdee')
            resp_text = "I can still guide you. Start with 2 easy full body days and a short daily walk. Share missing info later for numbers."
            return HistoryChatResponse(response=resp_text, profile=merged_profile, tdee=None, missing=merged_missing, asked_this_intent=[], intent='tdee')

        # ---- General intent path w/ RAG grounding ----
        retrieved: List[Dict[str, str]] = []
        try:
            if hasattr(self, '_rag_index') and self._rag_index is not None:
                retrieved = self._rag_index.retrieve(last_user, k=settings.max_retrieval_chunks)  # type: ignore
        except Exception as e:  # noqa: BLE001
            logger.warning("RAG retrieval failed: %s", e)
            retrieved = []

        retrieved_strings: List[str] = []
        if retrieved:
            # Build context block per spec
            context_lines = []
            for r in retrieved:
                chunk_text = r['text'].strip()
                if len(chunk_text) > 500:
                    chunk_text = chunk_text[:500] + '...'
                context_lines.append(f"[{r['source']}] {chunk_text}")
            retrieved_strings = context_lines

        # Deterministic fallback path when no model configured
        if intent != 'tdee' and not self._model:
            fallback = self._fallback_general(last_user, retrieved_strings, profile)
            return HistoryChatResponse(response=fallback, profile=profile, tdee=None, missing=missing, asked_this_intent=[], intent=intent)

        prompt = self._build_prompt_general(last_user, retrieved_strings)
        model_reply = self._generate_response(prompt)
        # Strip cliché safety lines unless the user asked about safety/pain
        if intent == 'general':
            model_reply = self._sanitize_cliches(last_user, model_reply)
        return HistoryChatResponse(response=model_reply, profile=profile, tdee=None, missing=missing, asked_this_intent=[], intent=intent)

    # ================== Internal Helpers ==================
    def _infer_activity_factor(self, text: str) -> Optional[float]:
        low = text.lower()
        job_hits = sum(1 for w in ACTIVE_JOB_WORDS if w in low)
        train_hits = sum(1 for w in RESISTANCE_TRAINING_WORDS if w in low)
        days = len(re.findall(r"(\b\d\s*days?\b|\b\d\s*x\s*per\s*week\b|\b\d\s*/\s*7\b)", low))
        hours = len(re.findall(r"\b\d{1,2}\s*hours?\b", low))
        if job_hits == 0 and train_hits == 0:
            return None
        if job_hits and train_hits:
            return ACTIVITY_FACTORS['moderate']
        if job_hits:
            if 'construction' in low or 'warehouse' in low or hours >= 2 and days >= 1:
                return ACTIVITY_FACTORS['moderate']
            return ACTIVITY_FACTORS['light']
        if train_hits:
            freq_match = re.search(r"(\b3|4|5)\s*(x|times)?\s*(a|per)?\s*week", low)
            if freq_match:
                return ACTIVITY_FACTORS['light']
            return ACTIVITY_FACTORS['sedentary']
        return None

    def _parse_profile_facts(self, text: str) -> Dict[str, Optional[Any]]:
        lower = text.lower()
        out: Dict[str, Optional[Any]] = {'sex': None, 'age': None, 'weight_kg': None, 'height_cm': None, 'activity_factor': None}
        g = RE_GENDER.search(lower)
        if g:
            first = g.group(1).lower()
            out['sex'] = 'male' if first[0] == 'm' or 'man' in first or 'boy' in first else 'female'
        a = RE_AGE.search(lower)
        if a:
            try:
                age = float(a.group(1))
                if 10 < age < 90:
                    out['age'] = age
            except Exception:  # noqa: BLE001
                pass
        w = RE_WEIGHT.search(lower)
        if w:
            try:
                val = float(w.group(1)); unit = w.group(2).lower()
                out['weight_kg'] = val if 'kg' in unit else val * 0.4536
            except Exception:  # noqa: BLE001
                pass
        h = RE_HEIGHT_FT_IN.search(lower) or RE_HEIGHT_FT_IN_WORDS.search(lower)
        if not h:
            loose = EXTRA_HEIGHT_FT_IN_LOOSE.search(lower)
            if loose:
                try:
                    ft_tmp = int(loose.group(1)); in_tmp = int(loose.group(2))
                    if 0 <= in_tmp <= 11:
                        h = loose
                except Exception:
                    pass
        if h:
            try:
                ft = float(h.group(1)); inc = float(h.group(2))
                out['height_cm'] = (ft*12 + inc) * 2.54
            except Exception:  # noqa: BLE001
                pass
        else:
            hcm = RE_HEIGHT_CM.search(lower)
            if hcm:
                try:
                    out['height_cm'] = float(hcm.group(1))
                except Exception:
                    pass
            else:
                hin = RE_HEIGHT_IN.search(lower)
                if hin:
                    try:
                        out['height_cm'] = float(hin.group(1)) * 2.54
                    except Exception:
                        pass
        for k,f in ACTIVITY_FACTORS.items():
            if k in lower:
                out['activity_factor'] = f
                break
        if out['activity_factor'] is None:
            inferred = self._infer_activity_factor(text)
            if inferred:
                out['activity_factor'] = inferred
        return out

    def _rebuild_profile(self, history: List[ChatMessage]) -> Dict[str, Optional[Any]]:
        profile: Dict[str, Optional[Any]] = {'sex': None, 'age': None, 'weight_kg': None, 'height_cm': None, 'activity_factor': None}
        for turn in history:
            if turn.role != 'user':
                continue
            facts = self._parse_profile_facts(turn.content)
            for k,v in facts.items():
                if v is not None:
                    profile[k] = v
        return profile

    def _profile_missing(self, profile: Dict[str, Optional[Any]]) -> List[str]:
        return [k for k in FIELD_ORDER if not profile.get(k)]

    def _is_tdee_intent(self, msg: str) -> bool:
        low = msg.lower()
        return any(k in low for k in TDEE_KEYWORDS) or bool(START_TDEE_TRIGGERS.search(low))

    def _is_safety_topic(self, msg: str) -> bool:
        return bool(SAFETY_TRIGGER.search(msg))

    def _detect_recall(self, last_user: str) -> Optional[str]:
        lower = last_user.lower()
        for field, pat in RECALL_PATTERNS.items():
            if pat.search(lower):
                return field
        return None

    def _already_asked(self, field: str, history: List[ChatMessage]) -> bool:
        scanned = 0
        for turn in reversed(history):
            if scanned > 30:
                break
            if turn.role == 'assistant':
                scanned += 1
                if ASK_PATTERNS[field].search(turn.content) and '?' in turn.content:
                    return True
        return False

    def _unresolved_tdee(self, history: List[ChatMessage]) -> bool:
        saw_tdee_request = False
        for turn in history:
            if turn.role == 'user' and self._is_tdee_intent(turn.content):
                saw_tdee_request = True
            if saw_tdee_request and turn.role == 'assistant':
                if re.search(r"(BMR).*(Daily burn)|Daily burn about", turn.content, re.I):
                    return False
        return saw_tdee_request

    def _compute_tdee(self, sex: str, weight_kg: float, height_cm: float, age: float, act: float) -> Tuple[float,float]:
        if sex.startswith('m'):
            bmr = 10*weight_kg + 6.25*height_cm - 5*age + 5
        else:
            bmr = 10*weight_kg + 6.25*height_cm - 5*age - 161
        return bmr, bmr*act

    def _format_tdee(self, profile: Dict[str, Any], bmr: float, tdee: float) -> str:
        low = int(tdee*0.95); high = int(tdee*1.05); b = int(bmr)
        bmi_note = ''
        try:
            bmi = profile['weight_kg']/((profile['height_cm']/100)**2)  # type: ignore
            if bmi < 16 or bmi > 40:
                bmi_note = ' If you can, talk to a health professional.'
        except Exception:
            pass
        return (f"Your body at rest uses about {b} calories (BMR). Daily burn about {low}-{high} calories (TDEE). "
                f"This is only a rough guess, not medical advice.{bmi_note}")

    def _format_known(self, profile: Dict[str, Optional[float]]) -> str:
        parts = []
        if profile['sex']: parts.append(f"sex={profile['sex']}")
        if profile['age']: parts.append(f"age={int(profile['age'])}")
        if profile['weight_kg']: parts.append(f"weight_kg={round(profile['weight_kg'],1)}")
        if profile['height_cm']: parts.append(f"height_cm={int(profile['height_cm'])}")
        if profile['activity_factor']: parts.append("activity=yes")
        return ', '.join(parts) if parts else 'none'

    def _build_prompt(self, history: List[ChatMessage], profile: Dict[str, Optional[float]], intent: str, missing: List[str]) -> str:
        MAX_CHARS = 4000
        trimmed: List[ChatMessage] = []
        total = 0
        for turn in reversed(history):
            c = len(turn.content)
            if total + c > MAX_CHARS:
                break
            trimmed.append(turn)
            total += c
        trimmed.reverse()
        system_lines = [
            APP_PERSONA,
            "Rules: Ask for only one missing data item when user wants calories. If already asked and still missing, give general starter advice without repeating. Keep it natural and concise; avoid filler like ‘That’s a great question’."
        ]
        if intent == 'tdee':
            system_lines.append(f"Known profile: {self._format_known(profile)}")
            if missing:
                system_lines.append(f"Missing (internal): {','.join(missing)}")
        convo_lines = []
        for t in trimmed:
            if t.role == 'system':
                convo_lines.append(f"System: {t.content}")
            elif t.role == 'user':
                convo_lines.append(f"User: {t.content}")
            else:
                convo_lines.append(f"Assistant: {t.content}")
        prompt = "\n".join([
            "System: " + " | ".join(system_lines),
            *convo_lines,
            "Assistant:"
        ])
        return prompt

    def _build_prompt_general(self, user_message: str, retrieved: List[str]) -> str:
        context_block = ""
        if retrieved:
            safe_chunks = []
            for c in retrieved[:settings.max_retrieval_chunks]:
                c_trim = c.strip()
                if len(c_trim) > 500:
                    c_trim = c_trim[:500] + "..."
                safe_chunks.append(c_trim)
            if safe_chunks:
                context_block = "\n\nContext:\n" + "\n".join(safe_chunks) + "\nOnly use this info if helpful. If unsure, be transparent and ask a brief follow‑up."
        safety_flag = "yes" if self._is_safety_topic(user_message) else "no"
        prompt = (
            f"Persona: {APP_PERSONA}\n"
            f"{context_block}\n"
            f"Instructions: {ANTI_HALLUCINATION_RULES} Use contractions. Be warm and conversational. Avoid filler like ‘That’s a great question’ or ‘As an AI’. "
            f"Avoid cliché safety lines like ‘listen to your body’ or ‘if you feel pain, stop’ unless the user asks about safety, pain, injury, form, or medical care.\n"
            f"SafetyAsked: {safety_flag}\n"
            f"User: {user_message}\n"
            f"Assistant:"
        )
        return prompt

    def _generate_response(self, prompt: str) -> str:
        if not self._model:
            return "Model not ready. Set GEMINI_API_KEY and retry."
        try:
            resp = self._model.generate_content(prompt, generation_config=genai.types.GenerationConfig(  # type: ignore
                temperature=0.55,
                max_output_tokens=180,
                top_p=0.9,
                top_k=40
            ))
            return (resp.text or '').strip()  # type: ignore
        except Exception as e:  # noqa: BLE001
            logger.error(f"Gemini failure: {e}")
            return "Sorry. Trouble answering now. Try again soon."

    def _handle_recall(self, field: str, profile: Dict[str, Any]) -> str:
        val = profile.get(field)
        if val is None:
            return "I do not have that yet."
        if field == 'height_cm':
            cm = round(val); total_inches = val/2.54; ft = int(total_inches//12); inc = int(round(total_inches%12))
            return f"You told me your height is about {cm} cm (~{ft}' {inc}\")."
        if field == 'weight_kg':
            kg = round(val,1); lbs = round(kg/0.4536)
            return f"Your weight saved is about {kg} kg (~{lbs} lb)."
        if field == 'age':
            return f"You said you are {int(val)} years old."
        if field == 'sex':
            return f"You told me your biological sex is {profile.get('sex')}."
        for name,f in ACTIVITY_FACTORS.items():
            if profile['activity_factor'] and abs(f - profile['activity_factor']) < 1e-6:
                return f"Saved activity level is {name} (factor {f})."
        return f"Saved activity factor is {profile['activity_factor']}"

    def _fallback_general(self, user_message: str, retrieved: List[str], profile: Dict[str, Any]) -> str:
        base = "I am in simple mode."
        context_sentence = ''
        if retrieved:
            first = retrieved[0].strip().replace('\n', ' ')
            m = re.split(r'[.!?]', first)
            if m and m[0]:
                snippet = m[0][:160].strip()
                context_sentence = f" Here’s a quick note from my files: {snippet}."
        if not context_sentence:
            if re.search(r'frequency|how often|days|week', user_message, re.I):
                context_sentence = " Try two full‑body days to start, plus a short daily walk."
            elif re.search(r'nutrition|eat|diet|protein', user_message, re.I):
                context_sentence = " Aim for simple, balanced meals—protein, veggies, and carbs you enjoy."
            elif re.search(r'form|injury|hurt|pain', user_message, re.I):
                context_sentence = " Ease in and stop if you feel sharp pain. Good form over speed."
            else:
                context_sentence = " Start small, then add a little each week."
        tail = " Tell me a bit more and I’ll tailor it."
        return (base + context_sentence + tail).strip()

    def _sanitize_cliches(self, user_message: str, reply: str) -> str:
        """Remove cliché safety phrases unless the user asked about safety/pain/injury.
        Keeps tone natural by filtering entire sentences containing banned phrases.
        """
        if self._is_safety_topic(user_message):
            return reply
        # Split reply into sentences conservatively
        parts = re.split(r"([.!?])", reply)
        rebuilt = []
        # Reconstruct while skipping cliché-containing sentences
        for i in range(0, len(parts), 2):
            sent = parts[i].strip()
            punct = parts[i+1] if i+1 < len(parts) else ''
            if not sent:
                continue
            if any(p.search(sent) for p in CLICHE_PATTERNS):
                continue
            rebuilt.append(sent + punct)
        cleaned = " ".join(s.strip() for s in rebuilt).strip()
        return cleaned or reply

rag_service = RAGService()
