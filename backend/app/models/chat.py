from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel

class ChatMessage(BaseModel):
    role: Literal['user','assistant','system']
    content: str

# New lightweight turn model (excludes 'system' role for client supplied turns)
class ChatTurn(BaseModel):
    role: Literal['user','assistant']
    content: str

class ChatQuery(BaseModel):
    history: List[ChatMessage]

# Extended models from original monolith (renamed for clarity)
class Profile(BaseModel):
    sex: Optional[str]
    age: Optional[float]
    weight_kg: Optional[float]
    height_cm: Optional[float]
    activity_factor: Optional[float]

class HistoryChatRequest(BaseModel):
    history: List[ChatMessage]

class HistoryChatResponse(BaseModel):
    response: str
    profile: Profile
    tdee: Optional[Dict[str, Any]]
    missing: List[str]
    asked_this_intent: List[str]
    intent: str

# New request/response models for refined /chat endpoint
class ChatRequest(BaseModel):
    message: str
    history: List[ChatTurn] = []  # prior conversation turns without the new message

class ChatResponse(BaseModel):
    response: str
    profile: Profile
    tdee: Optional[Dict[str, Any]]
    missing: List[str]
    asked_this_intent: List[str]
    intent: str
