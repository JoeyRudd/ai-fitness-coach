from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging so we can see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Gemini AI model
model = None

# Define the AI coach personality
AI_COACH_PERSONA = """You are a friendly and encouraging AI fitness coach. Your target user is a 45-year-old beginner who needs simple, clear, and safe advice.

Guidelines:
- Use positive, encouraging language
- Explain concepts in plain English (e.g., say "burning more calories than you eat" instead of "caloric deficit")
- Always prioritize safety - recommend consulting a doctor before starting new routines
- Keep responses helpful but detailed enough to be actionable
- Provide 2-3 specific tips or recommendations when possible"""

def initialize_ai():
    """Initialize Gemini AI model"""
    global model
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("❌ GEMINI_API_KEY not found in environment variables!")
        logger.info("Please add your Gemini API key to a .env file:")
        logger.info("GEMINI_API_KEY=your_api_key_here")
        return False
    
    try:
        logger.info("🔧 Configuring Gemini AI...")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("✅ Gemini AI configured successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Gemini: {e}")
        return False

def generate_ai_response(user_message: str) -> str:
    """Generate a response using Gemini AI"""
    if model is None:
        logger.warning("Gemini model not initialized - trying to initialize...")
        if not initialize_ai():
            return "❌ AI model failed to load. Please check your GEMINI_API_KEY and restart the server."
    
    logger.info(f"🤖 Generating Gemini response for: {user_message}")
    
    # Create prompt with personality
    prompt = f"""{AI_COACH_PERSONA}

User question: {user_message}

Please provide a helpful, encouraging fitness coaching response:"""
    
    try:
        # Generate response with Gemini
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=300,
                top_p=0.8,
                top_k=40
            )
        )
        
        ai_response = response.text.strip()
        logger.info(f"✅ Gemini response ({len(ai_response)} chars): {ai_response[:50]}...")
        return ai_response
        
    except Exception as e:
        logger.error(f"❌ Gemini API failed: {e}")
        return "I'm having trouble connecting to my AI brain right now. Please try again in a moment!"

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.on_event("startup")
async def startup_event():
    """Initialize Gemini AI when the app starts"""
    logger.info("🚀 Starting AI Fitness Coach with Gemini...")
    initialize_ai()

@app.get("/")
async def root():
    return {"message": "AI Fitness Coach with Gemini is running!", "ai_status": "Gemini 1.5 Flash" if model else "Not initialized"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat with the AI fitness coach using Gemini"""
    response = generate_ai_response(request.message)
    return ChatResponse(response=response)
