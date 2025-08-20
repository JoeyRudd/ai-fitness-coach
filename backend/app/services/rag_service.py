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
    "You are a knowledgeable, encouraging fitness coach who talks like a real person. "
    "Be warm and supportive, but vary your language naturally. "
    "Give specific, actionable advice based on what you know about the user. "
    "Keep responses concise (1-2 short paragraphs). "
    "Be direct and confident in your recommendations. "
    "Avoid repetitive phrases or robotic language. "
    "Focus on practical guidance that beginners can actually follow."
)
GEMINI_MODEL_NAME = settings.gemini_model_name
# Prompt instruction block appended after persona & optional context
ANTI_HALLUCINATION_RULES = (
    "If something isn't in the context or user message, provide general but safe guidance based on what you do know. "
    "Only ask clarifying questions if absolutely necessary for safety reasons. "
    "Be proactive and solution-oriented with available information. "
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
        self._desired_length = "medium"
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
        profile = self._rebuild_profile(history)
        # Persist the most recent profile for prompt builders that reference it
        try:
            setattr(self, 'last_profile', dict(profile))
        except Exception:
            pass
        user_turns = [t for t in history if t.role == 'user']
        # Only intercept protein questions if there is at least one user message
        if user_turns:
            last_user = user_turns[-1].content
            last_user_lower = last_user.lower()
            protein_patterns = [
                "how much protein",
                "protein should i eat",
                "protein do i need",
                "protein goal",
                "protein intake",
                "protein per day"
            ]
            if any(p in last_user_lower for p in protein_patterns):
                weight_kg = profile.get('weight_kg')
                if weight_kg:
                    weight_lb = round(weight_kg / 0.4536)
                    min_protein = int(weight_lb * 0.8)
                    max_protein = int(weight_lb * 1.0)
                    resp = (
                        f"A good target is 0.8–1 gram of protein per pound of body weight per day. "
                        f"For your weight ({weight_lb} lbs), that's about {min_protein}–{max_protein} grams of protein daily. "
                        f"Focus on simple, lean sources like chicken, fish, eggs, beans, or Greek yogurt."
                    )
                    return HistoryChatResponse(response=resp, profile=profile, tdee=None, missing=[], asked_this_intent=[], intent='protein')
                # If weight is missing, fall through to normal logic (Gemini will be prompted)
        else:
            last_user = ""
        # Match original behavior of /chat2 endpoint.
        user_turns = [t for t in history if t.role == 'user']
        empty_profile_dict = {'sex': None,'age': None,'weight_kg': None,'height_cm': None,'activity_factor': None}
        if not user_turns:
            return HistoryChatResponse(response="Please send a message.", profile=empty_profile_dict, tdee=None, missing=FIELD_ORDER, asked_this_intent=[], intent='none')
        last_user = user_turns[-1].content
        missing = self._profile_missing(profile)

        # Detect intent from last user message

        # Gather all user messages for Gemini context
        user_history_text = '\n'.join([t.content for t in user_turns])

        # Check if this is a TDEE intent or if we're continuing a TDEE conversation
        if self._is_tdee_intent(last_user):
            intent = 'tdee'
        elif self._unresolved_tdee(history):
            intent = 'tdee'
        else:
            intent = 'general'

        # Decide desired response length up-front for this turn
        self._desired_length = self._decide_response_length(intent, last_user, history)

        # If it's just a greeting/ack and short mode, reply briefly without extra advice
        if self._desired_length == 'short':
            ack = self._is_greeting_or_ack(last_user)
            if ack:
                return HistoryChatResponse(response=ack, profile=profile, tdee=None, missing=missing, asked_this_intent=[], intent=intent)

        recall_field = self._detect_recall(last_user)
        if recall_field:
            resp_text = self._handle_recall(recall_field, profile)
            return HistoryChatResponse(response=resp_text, profile=profile, tdee=None, missing=missing, asked_this_intent=[], intent='recall')

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

            # Only require truly essential fields for TDEE calculation
            essentials = ['sex','age','weight_kg','height_cm','activity_factor']
            merged_missing = [k for k in essentials if not merged_profile.get(k)]

            # If enough info, always provide a best-effort estimate
            enough_info = all(merged_profile.get(k) for k in ['sex','age','weight_kg','height_cm','activity_factor'])
            if enough_info:
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
                # Detect user goal for calorie adjustment
                goal = 'maintain'
                last_user_lower = last_user.lower()
                if any(word in last_user_lower for word in ["cut", "lose weight", "losing weight", "fat loss", "weight loss", "deficit"]):
                    goal = 'cut'
                elif any(word in last_user_lower for word in ["bulk", "gain weight", "gaining weight", "surplus"]):
                    goal = 'bulk'
                # Calculate calorie targets
                if goal == 'cut':
                    cut_low = max(1200, int(tdee_val - 500))
                    cut_high = int(tdee_val - 300)
                    resp_text = (
                        f"For weight loss, aim for {cut_low}-{cut_high} calories per day (300-500 below your TDEE of {int(tdee_val)}). "
                        f"This creates a sustainable deficit for about 1 pound of weight loss per week. "
                        f"Don't go below 1200 calories without medical supervision."
                    )
                elif goal == 'bulk':
                    bulk_low = int(tdee_val + 200)
                    bulk_high = int(tdee_val + 400)
                    resp_text = (
                        f"For muscle gain, target {bulk_low}-{bulk_high} calories per day (200-400 above your TDEE of {int(tdee_val)}). "
                        f"This provides enough energy for muscle growth without excessive fat gain. "
                        f"Focus on getting adequate protein and progressive overload in your training."
                    )
                else:
                    resp_text = self._format_tdee(merged_profile, bmr_val, tdee_val)
                tdee_obj = {'bmr': int(bmr_val), 'tdee': int(tdee_val), 'range': [low, high]}
                return HistoryChatResponse(response=resp_text, profile=merged_profile, tdee=tdee_obj, missing=[], asked_this_intent=[], intent='tdee')

            # If not enough info, only ask for the first missing essential that hasn't already been provided
            ask_field: Optional[str] = None
            for f in essentials:
                if f in merged_missing and not self._already_asked(f, history):
                    ask_field = f
                    break
            
            if ask_field:
                # Check if we have enough context to provide helpful guidance anyway
                conversation_context = self._extract_conversation_context(history) if history else {}
                has_helpful_context = (
                    conversation_context.get('fitness_level') or 
                    conversation_context.get('goals') or 
                    conversation_context.get('access_equipment')
                )
                
                if has_helpful_context:
                    # Provide helpful guidance based on what we know, then gently ask for missing info
                    guidance = self._provide_tdee_guidance_with_context(merged_profile, conversation_context)
                    human = FIELD_HUMAN[ask_field]
                    resp_text = f"{guidance}\n\nTo get your specific calorie numbers, what's your {human}?"
                    return HistoryChatResponse(response=resp_text, profile=merged_profile, tdee=None, missing=merged_missing, asked_this_intent=[ask_field], intent='tdee')
                else:
                    # No helpful context, just ask for the missing info
                    human = FIELD_HUMAN[ask_field]
                    resp_text = f"What's your {human}?" if ask_field != 'activity_factor' else "What's your activity level? (sedentary, light, moderate, very, extra)"
                    return HistoryChatResponse(response=resp_text, profile=merged_profile, tdee=None, missing=merged_missing, asked_this_intent=[ask_field], intent='tdee')
            
            # If user has already been asked for all essentials, give general advice
            resp_text = "I can still help! Do 2 full-body strength days per week and walk daily. Share your stats when you're ready for specific numbers."
            return HistoryChatResponse(response=resp_text, profile=merged_profile, tdee=None, missing=merged_missing, asked_this_intent=[], intent='tdee')

        # ---- General intent path w/ RAG grounding ----
        retrieved: List[Dict[str, str]] = []
        try:
            if hasattr(self, '_rag_index') and self._rag_index is not None:
                # Dynamic k: short queries benefit from a slightly larger k
                q_words = len((last_user or "").split())
                dyn_k = 5 if q_words <= 3 else settings.max_retrieval_chunks
                # Use hybrid RRF retrieval for better results
                retrieved = self._rag_index.hybrid_retrieve(last_user, k=dyn_k)  # type: ignore
                logger.info("RAG retrieval successful: %d results for query '%s'", len(retrieved), last_user)
                for i, r in enumerate(retrieved):
                    logger.info("Retrieved %d: [%s] %s...", i, r['source'], r['text'][:100])
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
                # Prefix with bracketed source so the model can optionally cite
                context_lines.append(f"[{r['source']}] {chunk_text}")
            retrieved_strings = context_lines

        # Check if we have enough context to provide helpful advice without asking questions
        conversation_context = self._extract_conversation_context(history) if history else {}
        has_sufficient_context = (
            conversation_context.get('fitness_level') or 
            conversation_context.get('goals') or 
            conversation_context.get('preferred_activities') or
            conversation_context.get('access_equipment') or
            any(profile.values())  # Has any profile information
        )
        
        # Special handling for workout split questions - these should always get specific guidance
        is_workout_split_question = any(term in (last_user or "").lower() for term in [
            "workout split", "training split", "split", "routine", "schedule", "full body", 
            "upper lower", "push pull", "ppl", "how often", "frequency", "workout", "training"
        ])

        # Deterministic fallback path when no model configured
        if intent != 'tdee' and not self._model:
            fallback = self._fallback_general(last_user, retrieved_strings, profile, history)
            return HistoryChatResponse(response=fallback, profile=profile, tdee=None, missing=missing, asked_this_intent=[], intent=intent)

        # If we have sufficient context, be more directive about not asking questions
        if has_sufficient_context:
            prompt = self._build_prompt_general(last_user, retrieved, history, is_workout_split_question)
        else:
            # For users with minimal context, still try to be helpful but may need to ask clarifying questions
            prompt = self._build_prompt_general(last_user, retrieved, history, is_workout_split_question)
        
        # Special handling for workout split questions when RAG fails or doesn't find relevant content
        if is_workout_split_question:
            # Check if RAG found workout split specific content
            has_workout_split_content = any(
                any(term in r.get('text', '').lower() for term in [
                    'workout split', 'training split', 'full body', 'upper lower', 'push pull', 'ppl',
                    'monday', 'wednesday', 'friday', 'schedule', 'routine'
                ])
                for r in retrieved
            )
            
            if not retrieved or not has_workout_split_content:
                # Provide specific workout split guidance when RAG doesn't find relevant content
                workout_split_response = self._get_workout_split_fallback(last_user)
                return HistoryChatResponse(response=workout_split_response, profile=profile, tdee=None, missing=missing, asked_this_intent=[], intent=intent)
        
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
        # Robust weight extraction: match 'I weigh 150 pounds', 'my weight is 150 lbs', 'weighing 150 pounds', 'weight: 150 lbs', etc.
        w = RE_WEIGHT.search(lower)
        if not w:
            import re
            weight_patterns = [
                r"(?:i weigh|i am weighing|my weight is|my current weight is|current weight is|weight is|weight:|weighing|weight=)\s*(\d{2,3})\s*(kg|kilograms|lbs|lb|pounds?)",
                r"(\d{2,3})\s*(kg|kilograms|lbs|lb|pounds?)\s*(is my weight|weight)"
            ]
            for pat in weight_patterns:
                alt_weight = re.search(pat, lower)
                if alt_weight:
                    val = float(alt_weight.group(1)); unit = alt_weight.group(2).lower()
                    out['weight_kg'] = val if 'kg' in unit else val * 0.4536
                    break
        else:
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
            for k, v in facts.items():
                # Only update if v is not None
                if v is not None:
                    profile[k] = v
                # If v is None, keep previous value (do not overwrite)
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
        # --- Conversation memory: include latest N turns, summarize older if needed ---
        MAX_TURNS = 12  # Number of most recent turns to include in full
        if len(history) > MAX_TURNS:
            # Summarize older turns
            summary = self._summarize_history(history[:-MAX_TURNS])
            trimmed = history[-MAX_TURNS:]
        else:
            summary = None
            trimmed = history
        # Add explicit user profile and instruction to not re-ask for known info
        user_profile_lines = [
            "User Profile:",
            f"  Sex: {profile.get('sex') if profile.get('sex') else 'unknown'}",
            f"  Age: {int(profile['age']) if profile.get('age') else 'unknown'}",
            f"  Weight (kg): {round(profile['weight_kg'],1) if profile.get('weight_kg') else 'unknown'}",
            f"  Height (cm): {int(profile['height_cm']) if profile.get('height_cm') else 'unknown'}",
            f"  Activity Level: {profile.get('activity_factor') if profile.get('activity_factor') else 'unknown'}"
        ]
        system_lines = [
            APP_PERSONA,
            "CRITICAL RULES:",
            "1. NEVER ask for information that is already provided in the user profile above",
            "2. NEVER ask follow-up questions unless absolutely necessary for safety reasons",
            "3. Use available information to give specific, actionable advice",
            "4. Be proactive and solution-oriented, not interrogative",
            "5. Keep responses concise and actionable (1-2 short paragraphs max)",
            "6. Avoid filler phrases like 'That's a great question' or 'As an AI'",
            "7. Vary your language naturally - don't use the same phrases repeatedly",
            "8. Be direct and confident - provide concrete numbers and specific advice when possible",
            *user_profile_lines
        ]
        
        # Extract conversation context to avoid asking for information already provided
        conversation_context = ""
        if history:
            context = self._extract_conversation_context(history)
            context_lines = []
            
            if context['fitness_level']:
                context_lines.append(f"Fitness Level: {context['fitness_level']}")
            if context['goals']:
                context_lines.append(f"Goals: {', '.join(context['goals'])}")
            if context['preferred_activities']:
                context_lines.append(f"Training Focus: {', '.join(context['preferred_activities'])}")
            if context['access_equipment']:
                context_lines.append(f"Equipment: {', '.join(context['access_equipment'])}")
            
            if context_lines:
                conversation_context = " | ".join(context_lines)
        
        if conversation_context:
            system_lines.append(f"Conversation Context: {conversation_context}")
            system_lines.append("USE THIS CONTEXT: Provide specific advice based on the user's fitness level, goals, and preferences. Do NOT ask for information already provided.")
        
        if summary:
            system_lines.append(f"Summary of earlier conversation: {summary}")
        if intent == 'tdee' and missing:
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

    def _summarize_history(self, history: List[ChatMessage]) -> str:
        """
        Summarize older conversation history into a short, factual summary for prompt context.
        Only user and assistant turns are included. This is a simple extractive summary.
        """
        facts = []
        for t in history:
            if t.role == 'user':
                facts.append(f"User: {t.content}")
            elif t.role == 'assistant':
                facts.append(f"Coach: {t.content}")
        # Limit summary length
        summary = ' | '.join(facts)
        if len(summary) > 400:
            summary = summary[:400] + '...'
        return summary

    def _extract_conversation_context(self, history: List[ChatMessage]) -> Dict[str, Any]:
        """Extract user preferences, goals, and context from conversation history."""
        context = {
            'fitness_level': None,
            'goals': [],
            'preferred_activities': [],
            'access_equipment': [],
            'time_availability': None,
            'experience_level': None,
            'injuries_limitations': [],
            'schedule_preferences': [],
            'nutrition_preferences': [],
            'motivation_factors': []
        }
        
        # Keywords to look for in user messages
        fitness_level_keywords = {
            'beginner': ['beginner', 'new', 'starting', 'first time', 'never worked out', 'just starting', 'never exercised', 'out of shape', 'sedentary'],
            'intermediate': ['intermediate', 'some experience', 'worked out before', 'moderate', 'been exercising', 'some fitness', 'active before'],
            'advanced': ['advanced', 'experienced', 'been working out', 'years of experience', 'fitness background', 'athletic background']
        }
        
        goal_keywords = {
            'muscle_building': ['muscle', 'build muscle', 'strength', 'get stronger', 'hypertrophy', 'gain muscle', 'muscle growth', 'bulk up', 'get bigger'],
            'weight_loss': ['lose weight', 'fat loss', 'slim down', 'burn fat', 'cut', 'deficit', 'shed pounds', 'get leaner'],
            'maintenance': ['maintain', 'maintenance', 'stay the same', 'keep current', 'maintain fitness', 'stay healthy'],
            'performance': ['performance', 'get better', 'improve', 'progress', 'endurance', 'stamina', 'functional fitness'],
            'general_health': ['health', 'healthy', 'wellness', 'feel better', 'energy', 'vitality', 'overall fitness']
        }
        
        activity_keywords = {
            'strength_training': ['strength training', 'weights', 'lifting', 'gym', 'resistance', 'bench press', 'squats', 'deadlift', 'overhead press', 'powerlifting'],
            'cardio': ['cardio', 'running', 'walking', 'cycling', 'swimming', 'jogging', 'treadmill', 'elliptical', 'rowing', 'aerobic'],
            'nutrition': ['nutrition', 'diet', 'eating', 'food', 'protein', 'carbs', 'calories', 'meal plan', 'supplements', 'macros'],
            'flexibility': ['flexibility', 'stretching', 'yoga', 'mobility', 'range of motion', 'flexible'],
            'functional': ['functional', 'movement', 'everyday', 'practical', 'real life', 'functional fitness']
        }
        
        equipment_keywords = {
            'gym': ['gym', 'fitness center', 'equipment', 'machines', 'barbell', 'dumbbells', 'cable machine', 'smith machine', 'full gym'],
            'home': ['home', 'at home', 'dumbbells', 'resistance bands', 'kettlebell', 'bench', 'home gym', 'garage gym'],
            'minimal': ['minimal equipment', 'no equipment', 'bodyweight only', 'just bodyweight', 'no weights', 'limited equipment']
        }
        
        time_keywords = {
            'very_busy': ['busy', 'no time', 'tight schedule', 'work long hours', 'family commitments', 'limited time'],
            'moderate_time': ['some time', 'moderate time', 'can make time', 'flexible schedule', 'part time'],
            'plenty_time': ['lots of time', 'flexible', 'can dedicate time', 'retired', 'student', 'part time work']
        }
        
        injury_keywords = ['injury', 'hurt', 'pain', 'knee', 'back', 'shoulder', 'hip', 'ankle', 'wrist', 'elbow', 'surgery', 'recovery', 'physical therapy']
        
        # Scan through user messages to build context
        for msg in history:
            if msg.role != 'user':
                continue
                
            content_lower = msg.content.lower()
            
            # Check fitness level
            for level, keywords in fitness_level_keywords.items():
                if any(k in content_lower for k in keywords):
                    context['fitness_level'] = level
                    context['experience_level'] = level
                    logger.debug("Detected fitness level: %s from message: %s", level, msg.content[:100])
            
            # Check goals
            for goal, keywords in goal_keywords.items():
                if any(k in content_lower for k in keywords):
                    if goal not in context['goals']:
                        context['goals'].append(goal)
                        logger.debug("Detected goal: %s from message: %s", goal, msg.content[:100])
            
            # Check preferred activities
            for activity, keywords in activity_keywords.items():
                if any(k in content_lower for k in keywords):
                    if activity not in context['preferred_activities']:
                        context['preferred_activities'].append(activity)
                        logger.debug("Detected activity: %s from message: %s", activity, msg.content[:100])
            
            # Check equipment access
            for equipment, keywords in equipment_keywords.items():
                if any(k in content_lower for k in keywords):
                    if equipment not in context['access_equipment']:
                        context['access_equipment'].append(equipment)
                        logger.debug("Detected equipment: %s from message: %s", equipment, msg.content[:100])
            
            # Check time availability
            for time_level, keywords in time_keywords.items():
                if any(k in content_lower for k in keywords):
                    context['time_availability'] = time_level
                    logger.debug("Detected time availability: %s from message: %s", time_level, msg.content[:100])
            
            # Check for injuries/limitations
            if any(k in content_lower for k in injury_keywords):
                # Extract specific injury mentions
                injury_mentions = []
                for keyword in injury_keywords:
                    if keyword in content_lower:
                        injury_mentions.append(keyword)
                if injury_mentions:
                    context['injuries_limitations'].extend(injury_mentions)
                    logger.debug("Detected injuries/limitations: %s from message: %s", injury_mentions, msg.content[:100])
            
            # Check for schedule preferences
            if any(word in content_lower for word in ['morning', 'evening', 'afternoon', 'night', 'early', 'late', 'weekend', 'weekday']):
                schedule_words = []
                for word in ['morning', 'evening', 'afternoon', 'night', 'early', 'late', 'weekend', 'weekday']:
                    if word in content_lower:
                        schedule_words.append(word)
                if schedule_words:
                    context['schedule_preferences'].extend(schedule_words)
            
            # Check for nutrition preferences
            if any(word in content_lower for word in ['vegetarian', 'vegan', 'keto', 'paleo', 'gluten free', 'dairy free', 'allergies', 'food preferences']):
                nutrition_words = []
                for word in ['vegetarian', 'vegan', 'keto', 'paleo', 'gluten free', 'dairy free', 'allergies', 'food preferences']:
                    if word in content_lower:
                        nutrition_words.append(word)
                if nutrition_words:
                    context['nutrition_preferences'].extend(nutrition_words)
        
        # Remove duplicates from lists
        context['goals'] = list(set(context['goals']))
        context['preferred_activities'] = list(set(context['preferred_activities']))
        context['access_equipment'] = list(set(context['access_equipment']))
        context['injuries_limitations'] = list(set(context['injuries_limitations']))
        context['schedule_preferences'] = list(set(context['schedule_preferences']))
        context['nutrition_preferences'] = list(set(context['nutrition_preferences']))
        
        logger.info("Final extracted context: %s", context)
        return context

    def _is_greeting_or_ack(self, message: str) -> Optional[str]:
        m = (message or '').strip().lower()
        if m in {"hi", "hey", "hello"}:
            return "Hi! How can I help?"
        if m in {"thanks", "thank you", "ty"}:
            return "You're welcome!"
        if m in {"ok", "okay", "got it", "cool", "great"}:
            return "Sounds good."
        return None

    def _decide_response_length(self, intent: str, user_message: str, history: Optional[List[ChatMessage]]) -> str:
        """Heuristic length selector: 'short' | 'medium' | 'long'."""
        msg = (user_message or "").strip().lower()

        # Very brief/acknowledgement style
        if msg in {"ok", "okay", "thanks", "thank you", "got it", "cool", "great"} or len(msg) <= 8:
            return "short"

        # Recall answers should be short
        if self._detect_recall(user_message):
            return "short"

        # Safety/pain topics may need a bit more context
        if self._is_safety_topic(user_message):
            return "medium"

        # TDEE path:
        # - If missing fields and we're asking for info: short
        # - If delivering numbers: medium
        if intent == "tdee":
            if self._unresolved_tdee(history or []):
                return "short"
            return "medium"

        # General intent
        simple_q = any(w in msg for w in ["what is", "how do i", "how to", "when should i"])
        if ("exercise" in msg or "exercises" in msg):
            # For exercise recommendation questions, allow more space to list specific items
            return "medium"
        if len(msg) <= 60 and ("?" in msg or simple_q):
            return "short"

        if any(w in msg for w in ["workout", "routine", "plan", "program", "split"]):
            return "long"
        if sum(w in msg for w in ["diet", "nutrition", "cardio", "strength", "protein", "calorie"]) >= 2:
            return "medium"

        return "medium"

    def _build_prompt_general(self, user_message: str, retrieved: List[Dict[str, str]], history: List[ChatMessage] = None, is_workout_split_question: bool = False) -> str:
        context_block = ""
        if retrieved:
            safe_chunks = []
            for c in retrieved[:settings.max_retrieval_chunks]:
                # Extract text from the retrieved dictionary
                chunk_text = c.get('text', '').strip()
                if len(chunk_text) > 500:
                    chunk_text = chunk_text[:500] + "..."
                safe_chunks.append(chunk_text)
            if safe_chunks:
                context_block = "\n\nContext:\n" + "\n".join(safe_chunks) + "\n\nCRITICAL: This context contains specific, expert fitness information. ALWAYS use the specific exercises, techniques, and advice mentioned in this context rather than generic fitness advice. If the context mentions specific exercises like 'Flat wide grip chest press' or 'Chest supported flared elbow row', use those exact names and details."
                
                # Special emphasis for workout split questions
                if is_workout_split_question:
                    context_block += "\n\nWORKOUT SPLIT FOCUS: When answering workout split questions, ALWAYS reference the specific workout splits mentioned in the context (Full Body, Upper/Lower, etc.) and provide the exact schedules and exercise recommendations from the knowledge base. Use the bracketed source filenames to ground your advice. If the context doesn't contain specific workout split information, supplement with the standard beginner recommendations: Full body 3x per week (Mon/Wed/Fri), Upper/Lower 4x per week, or Push/Pull/Legs 6x per week."
        # Always include user profile for general advice
        profile = getattr(self, 'last_profile', None)
        user_profile_lines = []
        if profile:
            user_profile_lines = [
                "User Profile:",
                f"  Sex: {profile.get('sex') if profile.get('sex') else 'unknown'}",
                f"  Age: {int(profile['age']) if profile.get('age') else 'unknown'}",
                f"  Weight (kg): {round(profile['weight_kg'],1) if profile.get('weight_kg') else 'unknown'}",
                f"  Height (cm): {int(profile['height_cm']) if profile.get('height_cm') else 'unknown'}",
                f"  Activity Level: {profile.get('activity_factor') if profile.get('activity_factor') else 'unknown'}"
            ]
        else:
            user_profile_lines = ["User Profile: unknown"]
        
        # Extract conversation context to avoid asking for information already provided
        conversation_context = ""
        if history:
            context = self._extract_conversation_context(history)
            context_lines = []
            
            if context['fitness_level']:
                context_lines.append(f"Fitness Level: {context['fitness_level']}")
            if context['goals']:
                context_lines.append(f"Goals: {', '.join(context['goals'])}")
            if context['preferred_activities']:
                context_lines.append(f"Training Focus: {', '.join(context['preferred_activities'])}")
            if context['access_equipment']:
                context_lines.append(f"Equipment: {', '.join(context['access_equipment'])}")
            
            if context_lines:
                conversation_context = "\n\nConversation Context:\n" + "\n".join([f"  {line}" for line in context_lines])
                conversation_context += "\n\nCRITICAL: Use this context to provide specific, personalized advice. NEVER ask for information already provided above. Be proactive and give actionable guidance based on what you know about the user."
                
                # Log the extracted context for debugging
                logger.info("Extracted conversation context: %s", context)
        
        safety_flag = "yes" if self._is_safety_topic(user_message) else "no"
        profile_text = '\n'.join(user_profile_lines)
        mode = getattr(self, "_desired_length", "medium")
        if mode == "short":
            length_instruction = "Keep it very brief: 1–2 sentences max."
        elif mode == "long":
            length_instruction = "Provide up to 2 short paragraphs. Use bullets only if essential."
        else:
            length_instruction = "One short paragraph (3–5 concise sentences)."
        prompt = (
            f"Persona: {APP_PERSONA}\n"
            f"CRITICAL RULES:\n"
            f"1. NEVER ask for information that is already provided in the user profile above\n"
            f"2. NEVER ask follow-up questions unless absolutely necessary for safety reasons\n"
            f"3. Use available information to give specific, actionable advice\n"
            f"4. Be proactive and solution-oriented, not interrogative\n"
            f"5. Keep responses concise and actionable (1-2 short paragraphs max)\n"
            f"6. Avoid filler phrases like 'That's a great question' or 'As an AI'\n"
            f"7. Vary your language naturally - don't use repetitive phrases\n"
            f"8. Be direct and confident - provide concrete numbers and specific advice when possible\n"
            f"9. NEVER reference training schedules, routines, or plans that aren't explicitly mentioned in the conversation or user profile\n"
            f"10. If the user asks for exercises, list 4–8 specific exercises from the context, using their exact names (e.g., 'Flat wide grip chest press').\n"
            f"11. When helpful, reference the bracketed source filename from the Context to ground your advice.\n"
            f"12. For workout split questions, ALWAYS provide the specific schedules and exercise recommendations from the knowledge base, including exact days and exercises. If the knowledge base doesn't contain specific workout split info, provide the standard beginner recommendations: Full body 3x per week (Mon/Wed/Fri with rest days), Upper/Lower 4x per week, or Push/Pull/Legs 6x per week.\n"
            f"{profile_text}"
            f"{conversation_context}\n"
            f"Use the user profile and conversation context above for any calculations or advice. Do not ask for information that is already present.\n"
            f"{context_block}\n"
            f"Response length: {length_instruction}\n"
            f"Instructions: {ANTI_HALLUCINATION_RULES} Use contractions. Be warm and conversational. "
            f"Avoid cliché safety lines like 'listen to your body' or 'if you feel pain, stop' unless the user asks about safety, pain, injury, form, or medical care.\n"
            f"SafetyAsked: {safety_flag}\n"
            f"User: {user_message}\n"
            f"Assistant:"
        )
        return prompt

    def _generate_response(self, prompt: str) -> str:
        if not self._model:
            return "Model not ready. Set GEMINI_API_KEY and retry."
        try:
            mode = getattr(self, "_desired_length", "medium")
            max_tokens = 300
            if mode == "short":
                max_tokens = 120
            elif mode == "long":
                max_tokens = 400

            resp = self._model.generate_content(prompt, generation_config=genai.types.GenerationConfig(  # type: ignore
                temperature=0.55,
                max_output_tokens=max_tokens,
                top_p=0.9,
                top_k=40
            ))
            text = (resp.text or '').strip()  # type: ignore
            # Enforce short/medium caps post-generation
            if mode == "short":
                parts = re.split(r"([.!?])", text)
                if parts:
                    text = (parts[0] + (parts[1] if len(parts) > 1 else '.')).strip()
            elif mode == "medium" and len(text) > 600:
                trimmed = text[:600].rstrip()
                if not trimmed.endswith('.'):
                    trimmed += '...'
                text = trimmed
            return text
        except Exception as e:  # noqa: BLE001
            logger.error(f"Gemini failure: {e}")
            return "Sorry. Trouble answering now. Try again soon."

    def _handle_recall(self, field: str, profile: Dict[str, Any]) -> str:
        val = profile.get(field)
        if val is None:
            return "I do not have that yet."
        if field == 'height_cm':
            cm = round(val); total_inches = val/2.54; ft = int(total_inches//12); inc = int(round(total_inches%12))
            return f"You told me your height is about {cm} cm (~{ft}' {inc}\")"
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

    def _get_workout_split_fallback(self, user_message: str) -> str:
        """Provide specific workout split guidance when RAG fails."""
        low_msg = (user_message or "").lower()
        
        if any(term in low_msg for term in ["full body", "fullbody", "full-body"]):
            return (
                "For beginners, a full body split 3 times per week is perfect! "
                "Do Monday, Wednesday, Friday with rest days between. "
                "Include exercises for legs (leg press, squats), push (chest press, shoulder press), "
                "pull (lat pulldown, rows), and core (planks). This hits all major muscle groups efficiently."
            )
        elif any(term in low_msg for term in ["upper lower", "upper/lower", "upper-lower"]):
            return (
                "Upper/Lower split works great for beginners with 4 days available! "
                "Monday/Thursday: Upper body (chest, back, shoulders, arms). "
                "Tuesday/Friday: Lower body (legs, glutes, calves). "
                "Wednesday, Saturday, Sunday: Rest. This gives more focus per muscle group."
            )
        elif any(term in low_msg for term in ["push pull", "push/pull", "push-pull", "ppl"]):
            return (
                "Push/Pull/Legs (PPL) is for more advanced beginners with 6 days available. "
                "Push days: chest, shoulders, triceps. Pull days: back, biceps. "
                "Leg days: quads, hamstrings, glutes, calves. "
                "Do each split twice per week with one rest day."
            )
        else:
            return (
                "For beginners, start with a full body split 3 times per week (Mon/Wed/Fri with rest days between). "
                "This hits all major muscle groups efficiently and allows proper recovery. "
                "Include compound movements like leg press, chest press, lat pulldown, and shoulder press. "
                "As you progress, you can move to upper/lower (4 days) or push/pull/legs (6 days)."
            )

    def _fallback_general(self, user_message: str, retrieved: List[str], profile: Dict[str, Any], history: List[ChatMessage] = None) -> str:
        base = "Here's what I can tell you:"
        context_sentence = ''
        # Always have a context dict for later conditional logic
        context: Dict[str, Any] = {}
        # Use conversation context to provide more personalized fallback responses
        if history:
            context = self._extract_conversation_context(history)
            
            # If we know the user's goals and fitness level, provide more specific advice
            if context['goals'] and context['fitness_level']:
                if 'muscle_building' in context['goals'] and context['fitness_level'] == 'beginner':
                    if 'gym' in context['access_equipment']:
                        context_sentence = " For building muscle as a beginner with gym access, do two full-body strength days per week. Focus on compound movements like leg press, chest press, lat pulldown, and shoulder press. Aim for 3-4 sets of 8-12 reps with proper form."
                    else:
                        context_sentence = " For building muscle as a beginner, do two full-body strength days per week. Use bodyweight exercises: push-ups, squats, lunges, planks, and resistance bands for rows and presses."
                elif 'weight_loss' in context['goals']:
                    if context['time_availability'] == 'very_busy':
                        context_sentence = " For weight loss with a busy schedule, do 2-3 short strength sessions (20-30 min) plus daily walking. Focus on compound movements and high-intensity intervals."
                    else:
                        context_sentence = " For weight loss, do 2-3 strength sessions per week plus 2-3 cardio sessions. Maintain a 300-500 calorie deficit."
                elif 'maintenance' in context['goals']:
                    context_sentence = " For maintenance, do 2-3 strength training sessions per week to maintain muscle mass and strength. Eat at your maintenance calories."
                elif 'general_health' in context['goals']:
                    context_sentence = " For general health, do 2-3 strength training sessions plus 2-3 cardio sessions per week. Walking daily is excellent for overall wellness."
                else:
                    context_sentence = " Do 2-3 strength training sessions per week focusing on compound movements and proper form."
            elif context['fitness_level'] == 'beginner':
                if 'gym' in context['access_equipment']:
                    context_sentence = " As a beginner with gym access, do 2-3 strength training days per week focusing on compound movements like leg press, chest press, and lat pulldown with proper form."
                else:
                    context_sentence = " As a beginner, do 2-3 strength training days per week using bodyweight exercises and resistance bands."
            elif context['injuries_limitations']:
                context_sentence = " Given your physical considerations, do low-impact exercises and focus on proper form. Consider consulting a physical therapist for personalized guidance."
            elif context['time_availability'] == 'very_busy':
                context_sentence = " With your busy schedule, do efficient workouts: 2-3 short strength sessions (20-30 min) plus daily walking. Compound movements give you the most bang for your buck."
        
        # If the user is asking for exercises or workout splits, try to surface specific items from the KB
        low_msg = (user_message or '').lower()
        is_workout_split_query = any(term in low_msg for term in [
            "workout split", "training split", "split", "routine", "schedule", "full body", 
            "upper lower", "push pull", "ppl", "how often", "frequency"
        ])
        
        # Special handling for workout split questions
        if is_workout_split_query and not context_sentence:
            context_sentence = self._get_workout_split_fallback(user_message)
        elif not context_sentence and (("exercise" in low_msg or "exercises" in low_msg) or is_workout_split_query) and retrieved:
            # Parse exercise lines of the form "**Muscle**: Exercise - ..."
            found: list[str] = []
            seen_pairs: set[str] = set()
            for blob in retrieved:
                # Work line-by-line to pick out category:name pairs
                for line in blob.splitlines():
                    line = line.strip()
                    m = re.match(r"^\*\*(.*?)\*\*\s*:\s*([^\-\n\r]+)", line)
                    if m:
                        muscle = m.group(1).strip()
                        exercise = m.group(2).strip()
                        key = f"{muscle}|{exercise}"
                        if key in seen_pairs:
                            continue
                        seen_pairs.add(key)
                        found.append(f"{exercise} ({muscle})")
                        if len(found) >= 8:
                            break
                if len(found) >= 8:
                    break
            if found:
                items = ", ".join(found[:6])
                context_sentence = f" From my knowledge base, great beginner-friendly picks include: {items}."
            elif is_workout_split_query:
                # Provide specific workout split guidance even without specific exercises
                context_sentence = " For beginners, start with a full body split 3x per week (Mon/Wed/Fri) with rest days between. This hits all major muscle groups efficiently and allows proper recovery."
        
        # Fall back to a generic snippet from RAG if nothing else was formed
        if not context_sentence and retrieved:
            first = retrieved[0].strip().replace('\n', ' ')
            m = re.split(r'[.!?]', first)
            if m and m[0]:
                snippet = m[0][:160].strip()
                context_sentence = f" Here's a quick note from my files: {snippet}."
        
        # Provide specific guidance based on the user's question
        if not context_sentence:
            if re.search(r'frequency|how often|days|week', user_message, re.I):
                if context.get('fitness_level') == 'beginner':
                    context_sentence = " Do 2-3 full-body strength training days per week (Mon/Wed/Fri with rest days between). Focus on compound movements like leg press, chest press, and lat pulldown. This full body split hits all major muscle groups efficiently."
                else:
                    context_sentence = " Do 3-4 training days per week, alternating between strength and cardio. Listen to your body and adjust based on recovery."
            elif re.search(r'nutrition|eat|diet|protein', user_message, re.I):
                if profile.get('weight_kg'):
                    weight_lb = round(profile['weight_kg'] / 0.4536)
                    protein_target = int(weight_lb * 0.8)
                    context_sentence = f" Get {protein_target}g of protein daily, along with complex carbs and healthy fats. For weight loss, eat in a 300-500 calorie deficit. For muscle building, eat at maintenance or a slight surplus."
                else:
                    context_sentence = " Get 0.8-1g of protein per pound of bodyweight daily, along with complex carbs and healthy fats. For weight loss, eat in a 300-500 calorie deficit. For muscle building, eat at maintenance or a slight surplus."
            elif re.search(r'form|injury|hurt|pain', user_message, re.I):
                context_sentence = " Focus on proper form over weight. Start with lighter weights and perfect your technique before progressing. Consider working with a trainer initially."
            elif re.search(r'cardio|running|walking', user_message, re.I):
                if context.get('fitness_level') == 'beginner':
                    context_sentence = " Do 20-30 minutes of moderate cardio 2-3 times per week. Walking, cycling, or swimming are great beginner options."
                else:
                    context_sentence = " Do 2-4 cardio sessions per week, mixing steady-state and interval training. Adjust intensity based on your fitness level."
            elif re.search(r'muscle|build muscle|strength|stronger', user_message, re.I):
                if context.get('fitness_level') == 'beginner':
                    context_sentence = " For building muscle as a beginner, do 2-3 full-body strength days per week. Focus on compound movements: leg press, chest press, lat pulldown, and shoulder press. Do 3-4 sets of 8-12 reps with proper form."
                else:
                    context_sentence = " For muscle building, focus on progressive overload with compound movements. Train each muscle group 2-3 times per week with 3-4 sets of 6-12 reps. Ensure adequate protein intake and recovery."
            elif re.search(r'workout|routine|plan', user_message, re.I):
                if context.get('fitness_level') == 'beginner':
                    context_sentence = " Here's a simple beginner routine: Day 1 - Leg press, chest press, lat pulldown (3x8-12 each). Day 2 - Rest or light walking. Day 3 - Shoulder press, rows, planks (3x8-12 each). Day 4 - Rest. Day 5 - Repeat Day 1. Focus on form and gradually increase weight."
                else:
                    context_sentence = " Consider a push/pull/legs split or upper/lower split. Train 4-5 days per week with 1-2 rest days. Focus on compound movements and progressive overload. Include 1-2 cardio sessions for conditioning."
            else:
                context_sentence = " Do 2-3 strength training sessions per week focusing on compound movements and proper form. Include 2-3 cardio sessions and prioritize protein intake for muscle building or weight loss."
        
        # Length-aware return
        mode = getattr(self, "_desired_length", "medium")
        if mode == "short":
            # Trim to the first sentence and keep it punchy
            first_sent = re.split(r'[.!?]', context_sentence.strip() or ".")[0].strip()
            if first_sent:
                return f"{base} {first_sent}."
            return base
        elif mode == "long":
            return (base + context_sentence).strip()
        else:
            # Medium: cap length to roughly one short paragraph
            para = (base + context_sentence).strip()
            if len(para) > 320:
                para = para[:320].rstrip()
                if not para.endswith("."):
                    para += "..."
            return para

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

    def _provide_tdee_guidance_with_context(self, profile: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Provide helpful guidance based on available context before asking for missing TDEE information."""
        guidance_parts = []
        
        # Fitness level guidance
        if context.get('fitness_level') == 'beginner':
            guidance_parts.append("As a beginner, start with 2-3 full-body strength training days per week.")
        elif context.get('fitness_level') == 'intermediate':
            guidance_parts.append("With your experience, you can handle 3-4 training days per week with more structured programming.")
        
        # Goal-based guidance
        if context.get('goals'):
            if 'weight_loss' in context['goals']:
                guidance_parts.append("For weight loss, combine strength training with cardio and maintain a 300-500 calorie deficit.")
            elif 'muscle_building' in context['goals']:
                guidance_parts.append("For muscle building, focus on progressive overload and eat at maintenance or a slight surplus.")
            elif 'maintenance' in context['goals']:
                guidance_parts.append("For maintenance, focus on consistent training and eating at your maintenance calories.")
        
        # Equipment guidance
        if context.get('access_equipment'):
            if 'gym' in context['access_equipment']:
                guidance_parts.append("With gym access, focus on compound movements like squats, deadlifts, and bench press.")
            elif 'home' in context['access_equipment']:
                guidance_parts.append("At home, use bodyweight exercises and resistance bands for effective workouts.")
            elif 'minimal' in context['access_equipment']:
                guidance_parts.append("Bodyweight exercises like push-ups, squats, and planks are excellent for building strength.")
        
        # Time availability guidance
        if context.get('time_availability') == 'very_busy':
            guidance_parts.append("With limited time, focus on compound movements that work multiple muscle groups efficiently.")
        
        # Combine guidance
        if guidance_parts:
            return " ".join(guidance_parts)
        else:
            return "I can help you create a personalized fitness plan. Let me know your goals and I'll provide specific recommendations."

rag_service = RAGService()
