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
from guardrails import parse_query_into_json_prompt
# from opneai_tools import tools_list
from MCP import tools_list
from MCP import Controller
import redis.asyncio as redis
from session_manager import SessionManager
from openai.types.chat import ChatCompletion
from threading import Thread
from persistant_storage import store_session_in_db
from contextlib import asynccontextmanager
import json
# @ App level reference for 3rd Party Services
# redis_client = None
session_manager: SessionManager
mcp_controller: Controller
background_task = None
client: OpenAI

logger = get_logger("FastAPI")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global session_manager, mcp_controller, client
    redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    session_manager = SessionManager(redis_client, session_ttl=3600)
    mcp_controller = Controller()
    client = OpenAI(
        api_key=settings.openai_api_key,
    )
    background_task = asyncio.create_task(store_session_in_db())
    logger.info("Background task for persisting sessions started.")
    yield
    # Clean up and release the resources
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            logger.info("Background task cancelled on shutdown.")


app = FastAPI(lifespan=lifespan)


# CORS setup for frontend (adjust origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # Use specific origin in production (e.g., ["https://yourfrontend.com"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Welcome to the Chatbot API!"}


@app.post("/async-chat", response_model=ChatResponse)
async def async_chat_endpoint(chat_request: ChatRequest):
    user_message = chat_request.message.strip()
    session_id = chat_request.session_id
    print(f"\n\nUser message: {user_message} \n  Session ID: {session_id}\n\n")
    # return ChatResponse(reply="Hello! When it comes to apples, taste can vary depending on the variety rather than just the color. However, here are some general guidelines:\n\n- **Red apples:** Varieties like Fuji, Gala, and Red Delicious are sweet and juicy.\n- **Green apples:** Granny Smith apples are tart and crisp, great if you like a tangy flavor.\n- **Yellow apples:** Golden Delicious apples are sweet and mellow.\n\nIf you prefer sweet apples, you might enjoy red or yellow ones. If you like tart and crisp, green apples are a good choice.\n\nWould you like me to recommend some specific apple products available on Digilog?If you can only buy two types of apples for your fruit salad, I recommend:\n\n1. **Fuji or Gala (Red apple)** – for sweetness and juiciness.\n2. **Granny Smith (Green apple)** – for tartness and crisp texture.\n\nThis combination will give your fruit salad a nice balance of sweet and tart flavors with a good crunch. Would you like me to help you find these apples on Digilog?",
    #     stuctural_data = [
    #         {
    #             "link": "https://digilog.pk/products/esp-01-esp8266-wifi-module-in-pakistan",
    #             "imageurl": "https://cdn.shopify.com/s/files/1/0559/7832/8150/files/ESP01_ESP_01_ESP8266_WiFi_Module_lahore_islamabad_karachi_multan_rawalpindi_1f5c781b-3dd8-4918-8043-18e105f0fd20.webp?v=1735049240&width=1400",
    #             "title": "Esp01 Esp 01 Esp8266 Wifi Module",
    #             "price": "290 PKR",
    #             "variants_options": ["Default Title"],
    #             "description": "ESP8266 WiFi Module provides integrated TCP/IP stack for easy WiFi access with any microcontroller. It features low power consumption, 1MB flash memory, supports SPI, UART, and integrated power management for efficient performance.",
    #             "type": "Product",
    #         },
    #         {
    #             "link": "https://digilog.pk/products/arduino-mkr1000-wifi-board-module-in-pakistan",
    #             "imageurl": "https://cdn.shopify.com/s/files/1/0559/7832/8150/files/Arduino_MKR1000_WiFi_Board_Module_In_Lahore_Karachi_Islamabad_Peshawar_Quetta_Mardan_Multan_Sibbi_Hyderabad_Faisalabad_Rawalpindi_Pakistan__1.webp?v=1735057239&width=1400",
    #             "title": "Arduino Mkr1000 Wifi Board Module",
    #             "price": "5,500 PKR",
    #             "variants_options": ["Default Title"],
    #             "description": "Arduino MKR1000 WiFi Board combines functional power with ease of use for IoT projects. It includes low power ARM MCU, encryption chip, LiPo battery charger, and supports WiFi b/g/n, ideal for secure and versatile networking.",
    #             "type": "Product",
    #         },
    #         {
    #             "link": "https://digilog.pk/products/ai-thinker-nodemcu-ai-wb2-13-wifi-bluetooth-5-0-module",
    #             "imageurl": "https://cdn.shopify.com/s/files/1/0559/7832/8150/files/Ai-ThinkerNodeMCU-Ai-WB2-13WiFiBluetooth5.0Module.webp?v=1735048366&width=1400",
    #             "title": "Ai-thinker Nodemcu-ai-wb2-13 Wifi Bluetooth 5.0 Module",
    #             "price": "900 PKR",
    #             "variants_options": ["Default Title"],
    #             "description": "Ai-Thinker WB2-13 Kit supports IEEE 802.11 b/g/n WiFi and Bluetooth BLE 5.0 with robust security protocols. Features include 32-bit RISC CPU, multiple interfaces, low power consumption, suitable for IoT, smart home, and wearable applications.",
    #             "type": "Product",
    #         },
    #         {
    #             "link": "https://digilog.pk/products/wt32-eth01-embedded-serial-port-networking-ethernet-ble-wifi-combo-gateway-mcu-esp32-wireless-module-board-wt32-eth01",
    #             "imageurl": "https://cdn.shopify.com/s/files/1/0559/7832/8150/files/WT32ETH01.webp?v=1735046836&width=1400",
    #             "title": "Wt32-eth01 Embedded Serial Port Networking Ethernet Ble Wifi Combo Gateway Mcu Esp32 Wireless Module Board Wt32 Eth01",
    #             "price": "3,800 PKR",
    #             "variants_options": ["Default Title"],
    #             "description": "WT32-ETH01 is a versatile IoT gateway module with ESP32 MCU offering WiFi, Bluetooth, Ethernet, and serial port connectivity. Perfect for industrial automation, smart home projects, and remote monitoring applications.",
    #             "type": "Product",
    #         },
    #         {'id': 'gid://shopify/Cart/1234567890', 'checkoutUrl': 'https://checkout.shopify.com/1234567890', 'subtotalAmount': '$129.99', 'lineItems': [{"merchandise_title": 'Blue T-Shirt', "quantity":2, "merchandise_price":'$29.99'},{"merchandise_title": 'Black Jeans', "quantity":12, "merchandise_price":'$59.99'}], 'type': 'Cart'},
    #         {'OrderID': '#12341', 'FinancialStatus': 'Paid', 'FulfillmentStatus': 'Shipped', 'CustomerName': 'Syed Raza Gufran', 'CustomerPhone': '0321******51', 'CustomerEmail': 'dev**********gmail.com', "Items": " - Surfing Product, Qty: 12, UnitPrice : 234 PKR \n  - Safety Product, Qty: 4, UnitPrice : 120 PKR \n  - Saketing Product, Qty: 6, UnitPrice : 234 PKR \n", 'ShippingAddress': 'st 12 house no 234 main colony newyork sector d', 'Total': '$249.99', 'type': 'Order'}
    #     ]
    # )
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if not session_id:
        session_id = await session_manager.create_session(
            {"data": None, "metadata": None}
        )  # Created User Chat History Data
    else:
        # Retrieve existing session data
        session_data = await session_manager.get_session(session_id)
        chat_request.load_history(session_data)
        if not True:
            raise HTTPException(status_code=404, detail="Session not found.")
        # print(f"\n $$$ Session data retrieved chat_request.n_history: \n{chat_request.n_history}\n\n\n\n\n\n\n")
    try:
        normal_query = await parse_into_json_prompt(chat_request)
        response = None
        async with AsyncOpenAI(
            api_key=settings.openai_api_key,
            http_client=DefaultAioHttpClient(timeout=200),
        ) as client:
            messages = chat_request.openai_msgs()
            response = await process_with_tools(client, chat_request, tools_list)

            chat_request.append_message(
                {"role": "user", "content": user_message, "name": "Customer"}
            )
            chat_request.append_message(response.choices[0].message.model_dump())
            chat_request.added_total_tokens(response.usage)

            logger.info(chat_request)

            logger.info(f"\n\nOpenAI response: {response}\n\n")
            # logger.info(f"\n\n History choices: {messages}")

            reply = str(response.choices[0].message.content).strip()
            stucture_output, reply = chat_request.extract_json_objects(reply)

            messages = chat_request.n_history

            latest_chat = chat_request.n_Serialize_chat_history(messages)
            await session_manager.update_session(session_id, latest_chat)

            print(f"\n Stuctural Data: {stucture_output}\n")
            print(f"\n Final Data: {reply}\n")
            print(f" Execution : {chat_request.activity_record}\n")

            return ChatResponse(
                reply=reply, stuctural_data=stucture_output, session_id=session_id
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
            chat_request.activity_record += " -> Output"
            return response

        chat_request.append_message(assistant_message.model_dump())
        chat_request.added_total_tokens(message_cost)

        chat_request = await mcp_controller.function_execution(
            chat_request, assistant_message.tool_calls
        )


async def parse_into_json_prompt(chat_request:ChatRequest):
    flag_categories = [
        # "DataQuery",
        # "ProductInfo",
        # "OrderFetch",
        # "CartFunctionality",
        # "ProductRelatedIntent",
        # "ProjectsDetails",
        "AnyMisleadingQuery",
        "RANDOM",
        "SystemAbuse",
    ]

    response = await parse_query_into_json_prompt(chat_request.message)
    if response.get("category") in flag_categories :
        chat_request.metadata.setdefault("flags", []).append(response["category"])

        chat_request.message = json.dumps(response)
        return False
    return True


if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
