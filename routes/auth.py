from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, Response
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_303_SEE_OTHER

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncEngine
from typing import Optional

import secrets
from jose import JWTError, jwt
from passlib.context import CryptContext

import asyncio
from datetime import datetime, timedelta

from config import sql_uri, settings, templates_path
from models import UserCreate, UserLogin, UserResponse, Token, LoginResponse


async def auth_check(request: Request):
    auth_header = request.headers.get("Authorization")
    token = None

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]

    if not token:
        token = request.cookies.get("access-token")

    if not token:
        accepts_html = "text/html" in request.headers.get("accept", "").lower()

        if accepts_html:
            # MUST raise, not return
            raise HTTPException(
                status_code=status.HTTP_303_SEE_OTHER,
                detail="Redirect",
                headers={"Location": "/auth"},
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
        )

    if token != settings.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    return True


templates = Jinja2Templates(directory=templates_path)


# ==================== CONFIGURATION ====================
SECRET_KEY = secrets.token_urlsafe(32)  # Generate secure key
REFRESH_SECRET_KEY = secrets.token_urlsafe(32)
ACCESS_TOKEN_EXPIRE_MINUTES = 5  # Short-lived
REFRESH_TOKEN_EXPIRE_DAYS = 30  # Long-lived

# Database
engine = create_async_engine(sql_uri, echo=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# ==================== DATABASE MODELS ====================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)


async def init_models(async_engine: AsyncEngine):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


asyncio.run(init_models(engine))


# ==================== UTILITY FUNCTIONS ====================
async def get_db():
    async with SessionLocal() as session:
        yield session


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=settings.auth_algo)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=settings.auth_algo)


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    try:
        secret = REFRESH_SECRET_KEY if token_type == "refresh" else SECRET_KEY
        payload = jwt.decode(token, secret, algorithms=[settings.auth_algo])

        if payload.get("type") != token_type:
            return None

        email = payload.get("sub")
        if email is None:
            return None
        return str(email)
    except JWTError:
        return None


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def authenticate_user(db, email, password):
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, str(user.hashed_password)):
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    email = verify_token(token, "access")
    if email is None:
        raise credentials_exception

    user = await get_user_by_email(db, email)

    if user is None:
        raise credentials_exception

    return user


# --- Router setup ---

router = APIRouter(
    prefix="/auth",
)


@router.get("/")
async def api_home(request: Request, prompt: str = "Untitled", mode: str = "view"):
    return templates.TemplateResponse(
        "auth.html", {"request": request, "endpoint": prompt}
    )


# ==================== AUTH ENDPOINTS ====================
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    if await get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user_data.password)

    db_user = User(
        email=user_data.email,
        name=user_data.name,
        hashed_password=hashed_password,
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    return db_user


@router.post("/login", response_model=LoginResponse)
async def login(
    response: Response, user_data: UserLogin, db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user(db, user_data.email, user_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@router.options("/login")
async def login_options():
    return Response(status_code=200)

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: Optional[str] = Cookie(None), db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token from cookie"""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found"
        )

    email = verify_token(refresh_token, "refresh")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user = await get_user_by_email(db, email)  # <- MUST await async DB call
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    # Create new access token
    access_token = create_access_token(data={"sub": user.email})

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(response: Response):
    """Logout by clearing refresh token cookie"""
    response.delete_cookie(key="refresh_token")
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


# ==================== PROTECTED ENDPOINTS (SAMPLES) ====================
@router.get("/protected/data")
async def get_protected_data(current_user: User = Depends(get_current_user)):
    return {"message": "Protected Data", "user": current_user.email}


@router.get("/protected/profile")
def get_user_profile(current_user: User = Depends(get_current_user)):
    """Another protected endpoint example"""
    return {
        "profile": {
            "name": current_user.name,
            "email": current_user.email,
            "id": current_user.id,
            "is_active": current_user.is_active,
        }
    }
