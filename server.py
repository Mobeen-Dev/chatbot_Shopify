from fastapi import FastAPI, HTTPException, status, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai._exceptions import OpenAIError
from models import ChatRequest, ChatResponse
from openai.types.chat import ChatCompletionMessageParam
import asyncio
import json
import uvicorn
from openai import DefaultAioHttpClient
from openai import AsyncOpenAI
from openai import OpenAI
from config import settings
from logger import get_logger
from opneai_tools import tools_list
from embed_and_save_vector import query_chroma
from Shopify import Shopify
import markdown


# #####################################################################
# ################## Helper Functions Start ###########################
# #####################################################################

# @ App level create a reference for Shopify API client
store = Shopify(settings.store, "ShopifyClient")

def get_products_data(query: str, top_k: int = 5) -> str:
    """
    Function for fetching product data based on a query.
    This interact with a Comapany Vector database.
    """
    results = query_chroma(query=query, top_k=top_k)
    return json.dumps(results) 

async def get_product_via_handle(handle: str) -> str:
    """
    Function to fetch complete product data using the product handle.
    This is used to get the most up-to-date product information.
    """
    product = await store.get_product_by_handle(handle)
    return str(product)
# #####################################################################
# ################## Helper Functions End #############################
# #####################################################################

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
    allow_headers=["*"]
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
    # return ChatResponse(reply="Hello! When it comes to apples, taste can vary depending on the variety rather than just the color. However, here are some general guidelines:\n\n- **Red apples:** Varieties like Fuji, Gala, and Red Delicious are sweet and juicy.\n- **Green apples:** Granny Smith apples are tart and crisp, great if you like a tangy flavor.\n- **Yellow apples:** Golden Delicious apples are sweet and mellow.\n\nIf you prefer sweet apples, you might enjoy red or yellow ones. If you like tart and crisp, green apples are a good choice.\n\nWould you like me to recommend some specific apple products available on Digilog?If you can only buy two types of apples for your fruit salad, I recommend:\n\n1. **Fuji or Gala (Red apple)** – for sweetness and juiciness.\n2. **Granny Smith (Green apple)** – for tartness and crisp texture.\n\nThis combination will give your fruit salad a nice balance of sweet and tart flavors with a good crunch. Would you like me to help you find these apples on Digilog?")
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
                tools=tools_list,
                messages=messages,
                tool_choice="auto",
                # max_tokens=650,
                # temperature=0.7,
            )
            
            assistant_message = response.choices[0].message
            print('\n\n\n\n')
            print('-' * 80)
            print(f"Assistant: {assistant_message}")
            print('-' * 80)
            if assistant_message.tool_calls:
                
                chat_request.append_message(
                                role=assistant_message.role,
                                content=None,# By Default
                                tool_calls=assistant_message.tool_calls
                            )
                
            print('\n\n\n\n')
            print('-' * 80)
            print(f"After 102: {chat_request.openai_messages}")
            print('-' * 80)
            print('\n\n\n\n')
                
            # Check if assistant called a tool
            if assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    if function_name == "get_products_data":
                        query = arguments["query"]
                        top_k = arguments.get("top_k_result", 5)

                        # Call the actual function
                        tool_output = get_products_data(query, top_k)

                        # Append tool response to messages
                        chat_request.append_message(
                            "tool",
                            content=tool_output,
                            tool_call_id =tool_call.id,
                            function_name=function_name                            
                        )
                    elif function_name == "get_product_via_handle":
                        handle = arguments["handle"]

                        # Call the actual function
                        tool_output = await get_product_via_handle(handle)

                        # Append tool response to messages
                        chat_request.append_message(
                            "tool",
                            content=tool_output,
                            tool_call_id =tool_call.id,
                            function_name=function_name                            
                        )
            messages = chat_request.openai_messages
            
            response = await client.chat.completions.create(
                model="gpt-4.1-mini",
                tools=tools_list,
                messages=messages,
                tool_choice="auto",
                # max_tokens=650,
                # temperature=0.7,
            )

            
            logger.info(f"OpenAI response: {response}")
            logger.info(f"\n\n History choices: {messages}")
            reply = str(response.choices[0].message.content).strip()
            reply_html = markdown.markdown(reply, extensions=['extra', 'codehilite'])
            print(f"Final reply HTML: {reply_html}")
            return ChatResponse(reply=reply_html, history=messages)

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

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)