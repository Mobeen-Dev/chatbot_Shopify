# Fast API
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# OpenAi
from openai import OpenAI  # try to remove this after Setting App performance

# App Config & Custom Utilities
from utils.logger import get_logger
from utils.PromptManager import PromptManager
from utils.session_manager import SessionManager
from config import settings, prompts_path, system_prompt, product_prompt, redis_url

# Build-in Utilities
import os
import asyncio
import uvicorn

# MCP
from MCP import Controller

# Routes
from routes.prompt import router as prompt_router
from routes.chat import router as chat_router

# DB Operations
import redis.asyncio as redis
from utils.persistant_storage import store_session_in_db

# Realtime Managment
from utils.file_change import handle_realtime_changes

# @ App State reference for 3rd Party Services
client: OpenAI
redis_client: redis.Redis
mcp_controller: Controller
background_task: asyncio.Task
prompt_manager: PromptManager
session_manager: SessionManager

logger = get_logger("FastAPI")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global background_task
    app.state.redis_client = redis.from_url(redis_url, decode_responses=True)
    app.state.session_manager = SessionManager(app.state.redis_client, session_ttl=3600)
    app.state.mcp_controller = Controller()
    app.state.client = OpenAI(
        api_key=settings.openai_api_key,
    )
    background_task = asyncio.create_task(store_session_in_db())
    app.state.prompt_manager = await PromptManager().init(system_prompt, product_prompt)
    asyncio.create_task(
        handle_realtime_changes(prompts_path, app.state.prompt_manager.reload)
    )
    app.state.logger = logger
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
app.include_router(chat_router)
app.include_router(prompt_router)

app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS setup for frontend (adjust origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Welcome to the Chatbot API!"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(os.path.join("static", "favicon.ico"))


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload_excludes=["./bucket/*.*", "./bucket/prompts/*.*"],
        reload=False,
    )
