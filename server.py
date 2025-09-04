from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from openai._exceptions import OpenAIError
from models import ChatRequest, ChatResponse
import asyncio
import uvicorn
from openai import DefaultAioHttpClient
from openai import AsyncOpenAI
from openai import OpenAI
from config import settings, llm_model
from logger import get_logger
# from opneai_tools import tools_list
from MCP import tools_list
from MCP import Controller
import redis.asyncio as redis
from session_manager import SessionManager
from openai.types.chat import ChatCompletion


# @ App level create a reference for 3rd Party Services
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
session_manager = SessionManager(redis_client, session_ttl=3600)
mcp_controller = Controller()

client = OpenAI(
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
    allow_headers=["*"]
)


@app.get("/")
async def root():
    return {"message": "Welcome to the Chatbot API!"}

@app.post("/async-chat", response_model=ChatResponse)
async def async_chat_endpoint(chat_request: ChatRequest):
    user_message = chat_request.message.strip()
    session_id = chat_request.session_id
    print(f"\n\nUser message: {user_message} \n  Session ID: {session_id}\n\n")
    # return ChatResponse(reply="Hello! When it comes to apples, taste can vary depending on the variety rather than just the color. However, here are some general guidelines:\n\n- **Red apples:** Varieties like Fuji, Gala, and Red Delicious are sweet and juicy.\n- **Green apples:** Granny Smith apples are tart and crisp, great if you like a tangy flavor.\n- **Yellow apples:** Golden Delicious apples are sweet and mellow.\n\nIf you prefer sweet apples, you might enjoy red or yellow ones. If you like tart and crisp, green apples are a good choice.\n\nWould you like me to recommend some specific apple products available on Digilog?If you can only buy two types of apples for your fruit salad, I recommend:\n\n1. **Fuji or Gala (Red apple)** – for sweetness and juiciness.\n2. **Granny Smith (Green apple)** – for tartness and crisp texture.\n\nThis combination will give your fruit salad a nice balance of sweet and tart flavors with a good crunch. Would you like me to help you find these apples on Digilog?")
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if not session_id:
        session_id = await session_manager.create_session({"data":None, "metadata":None}) # Created User Chat History Data
    else:
        # Retrieve existing session data
        session_data = await session_manager.get_session(session_id)
        chat_request.load_history(session_data)
        if not True:
            raise HTTPException(status_code=404, detail="Session not found.")
        print(f"\n $$$ Session data retrieved chat_request.n_history: \n{chat_request.n_history}\n\n\n\n\n\n\n")
    try:
        response = None
        async with AsyncOpenAI(
            api_key=settings.openai_api_key,
            http_client=DefaultAioHttpClient(timeout=60),
        ) as client:

            messages = chat_request.openai_msgs()
            response = await process_with_tools(client, chat_request, tools_list) 
            
            
            chat_request.append_message({"role": "user", "content": user_message, "name": "Customer"})
            chat_request.append_message(response.choices[0].message.model_dump())
            chat_request.added_total_tokens(response.usage)
            
            logger.info(chat_request)  
            
            logger.info(f"\n\n\n\n\nOpenAI response: {response}\n\n\n\n\n\n")
            # logger.info(f"\n\n History choices: {messages}")
            
            reply = str(response.choices[0].message.content).strip() 
            stucture_output, reply = chat_request.extract_json_objects(reply)
            

            messages = chat_request.n_history
            
            latest_chat = chat_request.n_Serialize_chat_history(messages)
            await session_manager.update_session(session_id, latest_chat)
            
            print(f"\n\nFinal Data: {reply}\n\n")
            
            return ChatResponse(
                reply=reply,
                stuctural_data=stucture_output,
                session_id=session_id
            )

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
    except Exception as e:  # noqa: F841
        logger.exception("Unexpected server error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error.",
        )

async def process_with_tools(client, chat_request, tools_list) -> ChatCompletion:
    """Handle recursive tool calls until no more tool calls are in the model's response."""
    
    while True:
        response = await client.chat.completions.create(
            model=llm_model,
            tools=tools_list,
            messages=chat_request.openai_msgs(),
            tool_choice="auto",
        )
        
        assistant_message = response.choices[0].message
        message_cost = response.usage
        
        if not assistant_message.tool_calls:
            # No more tools, final AI reply
            return response
        
        chat_request.append_message(assistant_message.model_dump())
        chat_request.added_total_tokens(message_cost)

        chat_request = await mcp_controller.function_execution(chat_request, assistant_message.tool_calls)



if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)