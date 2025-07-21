from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import openai

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# CORS setup for frontend (adjust origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use specific origin in production (e.g., ["https://yourfrontend.com"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request schema
class ChatRequest(BaseModel):
    message: str

# Response schema
class ChatResponse(BaseModel):
    reply: str
    
@app.get("/")
async def root():
    return {"message": "Welcome to the Chatbot API!"}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatRequest):
    user_message = chat_request.message

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",  # or "gpt-3.5-turbo"
            messages=[
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500
        )

        
        reply = str(response.choices[0].message.content)
        return ChatResponse(reply=reply)

    except Exception as e:
        print(f"OpenAI API Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Chatbot failed to respond.")
