from fastapi import FastAPI, HTTPException, status, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai._exceptions import OpenAIError
from models import ChatRequest, ChatResponse
from openai.types.chat import ChatCompletionMessageParam
import asyncio
from openai import DefaultAioHttpClient
from openai import AsyncOpenAI
from openai import OpenAI
from config import settings
from logger import get_logger



client = OpenAI(
    # This is the default and can be omitted
    api_key=settings.openai_api_key,
)
logger = get_logger("FastAPI")
app = FastAPI()

# CORS setup for frontend (adjust origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use specific origin in production (e.g., ["https://yourfrontend.com"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Welcome to the Chatbot API!"}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatRequest):
    user_message = chat_request.message
    print(f"User message: {user_message}")

    try:
        response = client.responses.create(
            model="gpt-4o",
            instructions="You are a coding assistant that talks like a UK citizen.",
            input=user_message,
        )

        
        # reply = str(response.choices[0].message.content)
        reply = str(response.output_text)
        return ChatResponse(reply=reply)

    except Exception as e:
        print(f"OpenAI API Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Chatbot failed to respond.")



@app.post("/async-chat", response_model=ChatResponse)
async def async_chat_endpoint(chat_request: ChatRequest):
    user_message = chat_request.message.strip()
    print(f"User message: {user_message}")
    return ChatResponse(reply="reply")
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        async with AsyncOpenAI(
            api_key=settings.openai_api_key,
            http_client=DefaultAioHttpClient(timeout=30),
        ) as client:

            messages = chat_request.openai_messages

            response = await client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                max_tokens=650,
                temperature=0.7,
            )

            reply = str(response.choices[0].message.content).strip()
            return ChatResponse(reply=reply)

    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to get response from language model.",
        )
    except asyncio.TimeoutError:
        logger.error("OpenAI API request timed out.")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Language model response timed out.",
        )
    except Exception as e:
        logger.exception("Unexpected server error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error.",
        )
