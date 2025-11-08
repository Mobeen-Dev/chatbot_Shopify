from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response
from fastapi import HTTPException
from fastapi.templating import Jinja2Templates
from config import settings, templates_path


# --- Auth check dependency ---
async def auth_check(request: Request):
    token = request.cookies.get("access-token")

    # Case 1: No cookie → redirect to /auth/
    if not token:
        # raise instead of return
        redirect = RedirectResponse(url="/", status_code=303)
        raise HTTPException(
            status_code=303, detail="Redirect", headers={"Location": "/"}
        )

    # Case 2: Cookie exists but invalid
    if token != settings.access_token:
        # simulate abrupt connection close
        return Response(status_code=444)

    return token


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