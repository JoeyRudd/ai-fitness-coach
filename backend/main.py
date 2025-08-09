from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import os, logging, re
from typing import Optional, Dict, Any, Tuple, List, Literal
from dotenv import load_dotenv

# ====================== Config & Setup ======================
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fitness_coach")

GEMINI_MODEL_NAME = "gemini-1.5-flash"
MODEL = None  # lazily initialized

APP_PERSONA = (
    "You are a friendly, concise beginner fitness coach. "
    "Target user: mid‑40s true beginner. Use very simple words and short sentences (3-6). "
    "No bullet lists. Positive, safe, plain language. Avoid medical claims."
)

# ====================== History Chat Models =================
class HistoryTurn(BaseModel):
    role: Literal['user','assistant','system']
    content: str

class Profile(BaseModel):
    sex: Optional[str]
    age: Optional[float]
    weight_kg: Optional[float]
    height_cm: Optional[float]
    activity_factor: Optional[float]

class HistoryChatRequest(BaseModel):
    history: List[HistoryTurn]

class HistoryChatResponse(BaseModel):
    response: str
    profile: Profile
    tdee: Optional[Dict[str, Any]]
    missing: List[str]
    asked_this_intent: List[str]
    intent: str

# ====================== Patterns & Constants ================
RE_GENDER = re.compile(r"\b(male|female|man|woman|boy|girl|m|f)\b", re.I)
RE_AGE = re.compile(r"\b(\d{2})\s*(?:yo|y/o|years?|yrs?)?\b", re.I)
RE_WEIGHT = re.compile(r"\b(\d{2,3})\s*(kg|kilograms|lbs|lb|pounds?)\b", re.I)
RE_HEIGHT_FT_IN = re.compile(r"(\d)[’']\s*(\d{1,2})")
RE_HEIGHT_FT_IN_WORDS = re.compile(r"(\d)\s*(?:ft|foot|feet)\s*(\d{1,2})\s*(?:in|inch|inches)?", re.I)
RE_HEIGHT_CM = re.compile(r"\b(\d{2,3})\s*cm\b", re.I)
RE_HEIGHT_IN = re.compile(r"\b(\d{2})\s*(?:in|inch|inches)\b", re.I)

ACTIVITY_FACTORS: Dict[str,float] = {
    'sedentary': 1.2,
    'light': 1.375,
    'moderate': 1.55,
    'very': 1.725,
    'extra': 1.9
}

# Keywords/phrases that imply a physically active job (heuristic)
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
    'sex': re.compile(r"(my\s+(sex|gender))", re.I),
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
    'sex': 'sex (male or female)',
    'age': 'age',
    'weight_kg': 'weight',
    'height_cm': 'height',
    'activity_factor': 'activity level (sedentary, light, moderate, very, extra)'
}

# ====================== Model Init ==========================

def init_model() -> bool:
    global MODEL
    if MODEL is not None:
        return True
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY missing")
        return False
    try:
        genai.configure(api_key=api_key)
        MODEL = genai.GenerativeModel(GEMINI_MODEL_NAME)
        logger.info("Gemini model initialized")
        return True
    except Exception as e:  # noqa: BLE001
        logger.error(f"Gemini init failed: {e}")
        return False

# ====================== Profile & Parsing ===================

def infer_activity_factor(text: str) -> Optional[float]:
    """Infer an activity factor from a free-form lifestyle / job description.
    Very lightweight heuristic: if user describes a standing / walking job a few days per week
    plus resistance training, classify as moderate. If only active job OR only lifting a few days, classify light.
    Return None if insufficient evidence.
    """
    low = text.lower()
    job_hits = sum(1 for w in ACTIVE_JOB_WORDS if w in low)
    train_hits = sum(1 for w in RESISTANCE_TRAINING_WORDS if w in low)
    # Detect days/hours patterns to increase confidence
    days = len(re.findall(r"(\b\d\s*days?\b|\b\d\s*x\s*per\s*week\b|\b\d\s*/\s*7\b)", low))
    hours = len(re.findall(r"\b\d{1,2}\s*hours?\b", low))
    if job_hits == 0 and train_hits == 0:
        return None
    # If both an active job (standing/walking) and lifting present, call it moderate
    if job_hits and train_hits:
        return ACTIVITY_FACTORS['moderate']
    # Only job OR only training: light unless heavy construction style keywords and many hours
    if job_hits:
        if 'construction' in low or 'warehouse' in low or hours >= 2 and days >= 1:
            return ACTIVITY_FACTORS['moderate']
        return ACTIVITY_FACTORS['light']
    if train_hits:
        # Lifting 3-4x/week alone usually still light overall for desk job
        freq_match = re.search(r"(\b3|4|5)\s*(x|times)?\s*(a|per)?\s*week", low)
        if freq_match:
            return ACTIVITY_FACTORS['light']
        return ACTIVITY_FACTORS['sedentary']
    return None

def parse_profile_facts(text: str) -> Dict[str, Optional[Any]]:
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
        except:  # noqa: E722
            pass
    w = RE_WEIGHT.search(lower)
    if w:
        try:
            val = float(w.group(1))
            unit = w.group(2).lower()
            out['weight_kg'] = val if 'kg' in unit else val * 0.4536
        except:  # noqa: E722
            pass
    h = RE_HEIGHT_FT_IN.search(lower) or RE_HEIGHT_FT_IN_WORDS.search(lower)
    if h:
        try:
            ft = float(h.group(1)); inc = float(h.group(2))
            out['height_cm'] = (ft*12 + inc) * 2.54
        except:  # noqa: E722
            pass
    else:
        hcm = RE_HEIGHT_CM.search(lower)
        if hcm:
            try:
                out['height_cm'] = float(hcm.group(1))
            except:  # noqa: E722
                pass
        else:
            hin = RE_HEIGHT_IN.search(lower)
            if hin:
                try:
                    out['height_cm'] = float(hin.group(1)) * 2.54
                except:  # noqa: E722
                    pass
    for k,f in ACTIVITY_FACTORS.items():
        if k in lower:
            out['activity_factor'] = f
            break
    # If not directly stated, attempt heuristic inference
    if out['activity_factor'] is None:
        inferred = infer_activity_factor(text)
        if inferred:
            out['activity_factor'] = inferred
    return out

def rebuild_profile(history: List[HistoryTurn]) -> Dict[str, Optional[Any]]:
    profile: Dict[str, Optional[Any]] = {'sex': None, 'age': None, 'weight_kg': None, 'height_cm': None, 'activity_factor': None}
    for turn in history:
        if turn.role != 'user':
            continue
        facts = parse_profile_facts(turn.content)
        for k,v in facts.items():
            if v is not None:
                profile[k] = v
    return profile

def profile_missing(profile: Dict[str, Optional[Any]]) -> List[str]:
    return [k for k in FIELD_ORDER if not profile.get(k)]

# ====================== Intent & Recall =====================

def is_tdee_intent(msg: str) -> bool:
    low = msg.lower()
    return any(k in low for k in TDEE_KEYWORDS) or bool(START_TDEE_TRIGGERS.search(low))

def detect_recall(last_user: str) -> Optional[str]:
    lower = last_user.lower()
    for field, pat in RECALL_PATTERNS.items():
        if pat.search(lower):
            return field
    return None

def already_asked(field: str, history: List[HistoryTurn]) -> bool:
    scanned = 0
    for turn in reversed(history):
        if scanned > 30:
            break
        if turn.role == 'assistant':
            scanned += 1
            if ASK_PATTERNS[field].search(turn.content) and '?' in turn.content:
                return True
    return False

def unresolved_tdee(history: List[HistoryTurn]) -> bool:
    """Return True if user previously asked about calories/TDEE and we have not yet provided a numeric TDEE answer."""
    saw_tdee_request = False
    for turn in history:
        if turn.role == 'user' and is_tdee_intent(turn.content):
            saw_tdee_request = True
        if saw_tdee_request and turn.role == 'assistant':
            # Consider TDEE delivered if assistant gave BMR/TDEE numbers pattern
            if re.search(r"(BMR).*(Daily burn)|Daily burn about", turn.content, re.I):
                return False
    return saw_tdee_request

# ====================== TDEE Helpers ========================

def compute_tdee(sex: str, weight_kg: float, height_cm: float, age: float, act: float) -> Tuple[float,float]:
    if sex.startswith('m'):
        bmr = 10*weight_kg + 6.25*height_cm - 5*age + 5
    else:
        bmr = 10*weight_kg + 6.25*height_cm - 5*age - 161
    return bmr, bmr*act

def format_tdee(profile: Dict[str, Any], bmr: float, tdee: float) -> str:
    low = int(tdee*0.95); high = int(tdee*1.05); b = int(bmr)
    bmi_note = ''
    try:
        bmi = profile['weight_kg']/((profile['height_cm']/100)**2)  # type: ignore
        if bmi < 16 or bmi > 40:
            bmi_note = ' If you can, talk to a health professional.'
    except:  # noqa: E722
        pass
    return (f"Your body at rest uses about {b} calories (BMR). Daily burn about {low}-{high} calories (TDEE). "
            f"This is only a rough guess, not medical advice.{bmi_note}")

# ====================== Prompt & Generation =================

def format_known(profile: Dict[str, Optional[float]]) -> str:
    parts = []
    if profile['sex']: parts.append(f"sex={profile['sex']}")
    if profile['age']: parts.append(f"age={int(profile['age'])}")
    if profile['weight_kg']: parts.append(f"weight_kg={round(profile['weight_kg'],1)}")
    if profile['height_cm']: parts.append(f"height_cm={int(profile['height_cm'])}")
    if profile['activity_factor']: parts.append("activity=yes")
    return ', '.join(parts) if parts else 'none'

def build_prompt(history: List[HistoryTurn], profile: Dict[str, Optional[float]], intent: str, missing: List[str]) -> str:
    MAX_CHARS = 4000
    trimmed: List[HistoryTurn] = []
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
        "Rules: Ask for only one missing data item when user wants calories. If already asked and still missing, give general starter advice without repeating. Keep sentences 3-6 words."
    ]
    if intent == 'tdee':
        system_lines.append(f"Known profile: {format_known(profile)}")
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
        "Assistant:"  # model continues
    ])
    return prompt

def generate_response(prompt: str) -> str:
    if not init_model():
        return "Model not ready. Set GEMINI_API_KEY and retry."
    try:
        resp = MODEL.generate_content(prompt, generation_config=genai.types.GenerationConfig(  # type: ignore
            temperature=0.55,
            max_output_tokens=180,
            top_p=0.9,
            top_k=40
        ))
        return (resp.text or '').strip()  # type: ignore
    except Exception as e:  # noqa: BLE001
        logger.error(f"Gemini failure: {e}")
        return "Sorry. Trouble answering now. Try again soon."

# ====================== FastAPI App =========================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def _startup():
    init_model()

@app.get("/")
async def root():
    return {"message": "AI Fitness Coach running", "model": GEMINI_MODEL_NAME}

@app.post("/chat2", response_model=HistoryChatResponse)
async def chat2(req: HistoryChatRequest) -> HistoryChatResponse:
    history = req.history
    user_turns = [t for t in history if t.role == 'user']
    if not user_turns:
        empty_profile = {'sex': None,'age': None,'weight_kg': None,'height_cm': None,'activity_factor': None}
        return HistoryChatResponse(response="Please send a message.", profile=empty_profile, tdee=None, missing=FIELD_ORDER, asked_this_intent=[], intent='none')
    last_user = user_turns[-1].content
    profile = rebuild_profile(history)
    missing = profile_missing(profile)

    # Recall intent
    recall_field = detect_recall(last_user)
    if recall_field:
        val = profile.get(recall_field)
        if val is None:
            resp_text = "I do not have that yet."
        else:
            if recall_field == 'height_cm':
                cm = round(val); total_inches = val/2.54; ft = int(total_inches//12); inc = int(round(total_inches%12))
                resp_text = f"You told me your height is about {cm} cm (~{ft}' {inc}\")."
            elif recall_field == 'weight_kg':
                kg = round(val,1); lbs = round(kg/0.4536)
                resp_text = f"Your weight saved is about {kg} kg (~{lbs} lb)."
            elif recall_field == 'age':
                resp_text = f"You said you are {int(val)} years old."
            elif recall_field == 'sex':
                resp_text = f"You told me you are {profile.get('sex')}."
            else:  # activity_factor
                for name,f in ACTIVITY_FACTORS.items():
                    if profile['activity_factor'] and abs(f - profile['activity_factor']) < 1e-6:
                        resp_text = f"Saved activity level is {name} (factor {f})."
                        break
                else:
                    resp_text = f"Saved activity factor is {profile['activity_factor']}"
        return HistoryChatResponse(response=resp_text, profile=profile, tdee=None, missing=missing, asked_this_intent=[], intent='recall')

    intent = 'tdee' if (is_tdee_intent(last_user) or unresolved_tdee(history)) else 'general'

    if intent == 'tdee':
        if not missing:
            bmr,tdee_val = compute_tdee(profile['sex'], profile['weight_kg'], profile['height_cm'], profile['age'], profile['activity_factor'])  # type: ignore
            low = int(tdee_val*0.95); high = int(tdee_val*1.05)
            resp_text = format_tdee(profile, bmr, tdee_val)
            return HistoryChatResponse(response=resp_text, profile=profile, tdee={'bmr': int(bmr), 'tdee': int(tdee_val), 'range': [low, high]}, missing=[], asked_this_intent=[], intent='tdee')
        ask_field: Optional[str] = None
        for f in FIELD_ORDER:
            if f in missing and not already_asked(f, history):
                ask_field = f
                break
        if ask_field:
            human = FIELD_HUMAN[ask_field]
            resp_text = f"Can you tell me your {human}?" if ask_field != 'activity_factor' else "What is your activity level? (sedentary, light, moderate, very, extra)"
            return HistoryChatResponse(response=resp_text, profile=profile, tdee=None, missing=missing, asked_this_intent=[ask_field], intent='tdee')
        resp_text = "I can still guide you. Start with 2 easy full body days and a short daily walk. Share missing info later for numbers."
        return HistoryChatResponse(response=resp_text, profile=profile, tdee=None, missing=missing, asked_this_intent=[], intent='tdee')

    # General coaching
    prompt = build_prompt(history, profile, intent, missing)
    model_reply = generate_response(prompt)
    return HistoryChatResponse(response=model_reply, profile=profile, tdee=None, missing=missing, asked_this_intent=[], intent=intent)

from app.main import app  # new modular app instance
