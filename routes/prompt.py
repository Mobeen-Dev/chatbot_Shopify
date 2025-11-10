from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends
import os
from fastapi.templating import Jinja2Templates
from datetime import datetime
from pathlib import Path
import yaml
from .auth import auth_check
import uvicorn
import datetime
from config import templates_path, system_prompt, product_prompt, prompts_path

product_prompt = Path(product_prompt)
system_prompt = Path(system_prompt)
prompts_path = Path(prompts_path)

router = APIRouter(
    prefix="/prompts", tags=["Prompt Engineering"], dependencies=[Depends(auth_check)]
)
# router = FastAPI()
templates = Jinja2Templates(directory=templates_path)


def handle_get(request: Request, file_path):
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Prompt file not found")

    # Load YAML
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=500, detail=f"YAML parsing error: {e}")

    # Extract only the prompt part
    prompt_text = data.get("prompt")
    if prompt_text is None:
        raise HTTPException(status_code=404, detail="No 'prompt' field found in YAML")

    # Prepare response headers
    last_modified = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
    headers = {"Last-Modified": last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT")}

    # Return only the prompt string
    return Response(prompt_text, media_type="text/plain", headers=headers)


async def handle_update(request: Request, file_path):
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Prompt file not found")

    # Read only the plain text from request body (the new prompt)
    new_prompt_text = await request.body()
    new_prompt_text = new_prompt_text.decode("utf-8").strip()

    if not new_prompt_text:
        raise HTTPException(status_code=400, detail="Prompt content is empty")

    # Load the current YAML
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise HTTPException(status_code=500, detail=f"YAML parsing error: {e}")

    # Update prompt + last_modified
    data["prompt"] = new_prompt_text
    today = datetime.date.today()
    data["last_modified"] = f"{today.day}/{today.month}/{str(today.year)[-2:]}"

    # Write it back
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Return success
    headers = {
        "Last-Modified": datetime.datetime.utcnow().strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )
    }
    return Response(
        "Prompt updated successfully", media_type="text/plain", headers=headers
    )


def handle_delete(file_path):
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Prompt file not found")

    # Load the current YAML (without deleting file)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise HTTPException(status_code=500, detail=f"YAML parsing error: {e}")

    # Update fields
    data["prompt"] = "This prompt has been removed by the user."
    today = datetime.date.today()
    data["last_modified"] = f"{today.day}/{today.month}/{str(today.year)[-2:]}"

    # Save it back
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    headers = {
        "Last-Modified": datetime.datetime.utcnow().strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )
    }
    return Response(
        "Prompt marked as deleted successfully",
        media_type="text/plain",
        headers=headers,
    )


@router.get("/")
def get_users(request: Request, prompt: str = "Untitled", mode: str = "view"):
    print("WOW")
    return templates.TemplateResponse("edit_prompt.html", {"request": request, "endpoint": prompt})


@router.post("/create")
async def create_prompt(request: Request, filename: str):
    file_path = os.path.join(prompts_path, filename)
    if os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="Prompt file already exists")

    body = await request.body()
    text = body.decode("utf-8")

    try:
        yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")

    return f"Created {filename}.yaml successfully."


@router.get("/edit")
def get_editor(request: Request, prompt: str = "Untitled", mode: str = "view"):
    # You can now access ?title=MyDoc&mode=edit from the URL
    return templates.TemplateResponse(
        "editor.html", {"request": request, "endpoint": prompt}
    )


@router.get("/system")
def get_system_prompt(request: Request):
    return handle_get(request, system_prompt)


@router.put("/system")
async def update_system_prompt(request: Request):
    return await handle_update(request, system_prompt)


@router.delete("/system")
def delete_system_prompt():
    return handle_delete(system_prompt)


@router.get("/product")
def get_product_prompt(request: Request):
    return handle_get(request, product_prompt)


@router.put("/product")
async def update_product_prompt(request: Request):
    return await handle_update(request, product_prompt)


@router.delete("/product")
def delete_product_prompt():
    return handle_delete(product_prompt)


# if __name__ == "__main__":
#     uvicorn.run("prompt:router", host="127.0.0.1", port=8000, reload=True)
