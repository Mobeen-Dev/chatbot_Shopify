from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response
from fastapi import Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from config import settings, templates_path

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_303_SEE_OTHER
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
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    return True



templates = Jinja2Templates(directory=templates_path)
# --- Router setup ---

router = APIRouter(
    prefix="/auth",
)



@router.get("/")
async def api_home(request: Request, prompt: str = "Untitled", mode: str = "view"):
    return templates.TemplateResponse(
        "auth.html", {"request": request, "endpoint": prompt}
    )