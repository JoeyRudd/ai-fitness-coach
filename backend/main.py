from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import pipeline
import logging

# Setup logging so we can see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Global variable to hold our AI model
generator = None

# Define the AI coach personality
AI_COACH_PERSONA = """You are a friendly and encouraging AI fitness coach. Your target user is a 45-year-old beginner who needs simple, clear, and safe advice.

Guidelines:
- Use positive, encouraging language
- Explain concepts in plain English (e.g., say "burning more calories than you eat" instead of "caloric deficit")
- Always prioritize safety - recommend consulting a doctor before starting new routines
- Suggest starting with light weights and simple exercises
- Keep responses helpful but concise"""

def initialize_ai():
    """Load the AI model when the app starts"""
    global generator
    logger.info("Loading AI model... this might take a minute the first time!")
    
    # Use GPT-2 for better text generation
    generator = pipeline(
        "text-generation",
        model="gpt2",
        device=-1,  # Use CPU (works on all machines)
        pad_token_id=50256
    )
    logger.info("AI model loaded successfully!")

def generate_ai_response(user_message: str) -> str:
    """Generate a response using the AI model with better control"""
    if generator is None:
        return "I'm still loading up! Please try again in a moment."
    
    # Create a much simpler prompt
    prompt = f"Question: {user_message}\nFitness Coach Answer:"
    
    try:
        # Generate with better parameters to avoid loops
        outputs = generator(
            prompt, 
            max_new_tokens=80,  # Limit new tokens instead of total length
            do_sample=True, 
            temperature=0.3,  # Lower temperature for more focused responses
            repetition_penalty=1.2,  # Prevent repetition
            pad_token_id=50256,
            eos_token_id=50256,
            num_return_sequences=1
        )
        
        response = outputs[0]['generated_text']
        
        # Extract just the answer part
        if "Fitness Coach Answer:" in response:
            ai_response = response.split("Fitness Coach Answer:")[-1].strip()
        else:
            ai_response = response.replace(prompt, "").strip()
        
        # Clean up and validate the response
        ai_response = ai_response.split('\n')[0]  # Take only first line
        ai_response = ai_response.strip()
        
        # If response is too short, repetitive, or weird, use fallback
        if (len(ai_response) < 10 or 
            ai_response.count(ai_response.split()[0] if ai_response.split() else '') > 3 or
            not ai_response):
            return get_fallback_response(user_message)
        
        return ai_response
    
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        return get_fallback_response(user_message)

def get_fallback_response(user_message: str) -> str:
    """Provide safe fallback responses for common fitness questions"""
    user_message_lower = user_message.lower()
    
    if any(word in user_message_lower for word in ['workout', 'exercise', 'train']):
        return "Great question! For beginners, I recommend starting with 20-30 minutes of light exercise 3 times per week. Always check with your doctor first!"
    
    elif any(word in user_message_lower for word in ['diet', 'eat', 'food', 'nutrition']):
        return "Good nutrition is key! Focus on eating plenty of vegetables, lean proteins, and whole grains. Stay hydrated and consider talking to a nutritionist for personalized advice."
    
    elif any(word in user_message_lower for word in ['weight', 'lose', 'gain']):
        return "Weight management comes down to burning slightly more calories than you eat for weight loss, or eating slightly more for weight gain. Start slowly and be patient with yourself!"
    
    elif any(word in user_message_lower for word in ['hello', 'hi', 'hey', 'howdy']):
        return "Hello! I'm your friendly fitness coach. I'm here to help you start your fitness journey safely. What would you like to know about exercise or nutrition?"
    
    else:
        return "I'm here to help with your fitness journey! Feel free to ask about workouts, nutrition, or getting started with exercise. Remember, it's always good to check with your doctor before starting a new routine."

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
    """Load the AI model when the app starts"""
    initialize_ai()

@app.get("/")
async def root():
    return {"message": "AI Fitness Coach Backend is running!"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat with the AI fitness coach"""
    response = generate_ai_response(request.message)
    return ChatResponse(response=response)
