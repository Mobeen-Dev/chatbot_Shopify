# Fast API
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exception_handlers import http_exception_handler

# OpenAi
from openai import OpenAI  # try to remove this after Setting App performance

# App Config & Custom Utilities
from utils.logger import get_logger
from utils.PromptManager import PromptManager
from utils.session_manager import SessionManager
from config import (
    settings,
    prompts_path,
    system_prompt,
    product_prompt,
    redis_url,
    templates_path,
    ALLOWED_ORIGIN_REGEX,
)

# Build-in Utilities
import os
import asyncio
import uvicorn

# MCP
from MCP import Controller

# Routes
from routes.prompt import router as prompt_router
from routes.chat import router as chat_router
from routes.auth import router as auth_router
from routes.knowledge_base import router as knowledge_base_router

# DB Operations
import redis.asyncio as redis
from utils.persistant_storage import store_session_in_db

# Realtime Managment
from utils.file_change import handle_realtime_changes
from fastapi.templating import Jinja2Templates

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


IS_PROD = settings.env == "DEP"  # Deployed Environment

app = FastAPI(
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json",
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    # only special-case 401; defer to default handler for the rest
    if exc.status_code != status.HTTP_401_UNAUTHORIZED:
        return await http_exception_handler(request, exc)

    accepts_html = "text/html" in request.headers.get("accept", "").lower()
    templates = request.app.state.templates

    if accepts_html:
        # render template for browsers
        return templates.TemplateResponse(
            "unauthorized.html",
            {"request": request, "reason": exc.detail},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # API clients -> JSON
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# CORS setup for frontend (adjust origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(chat_router)
app.include_router(prompt_router)
app.include_router(auth_router)
app.include_router(knowledge_base_router)


app.state.templates = Jinja2Templates(directory=templates_path)


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
