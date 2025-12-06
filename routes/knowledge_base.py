import os
from datetime import datetime
from pymongo import AsyncMongoClient
from typing import Optional, List, Dict, Any
from pymongo import ASCENDING, DESCENDING
from fastapi.responses import JSONResponse
from fastapi import APIRouter, FastAPI, HTTPException, status, Query, Depends

from models import FAQCreateModel, FAQUpdateModel, FAQOutModel
from config import mongoDb_uri

# ----------------------------------------------------
# CONSTANTS (as requested: ALL CAPS)
# ----------------------------------------------------
DB_NAME: str = "knowledge_base"
COLLECTION_NAME: str = "faqs"
PAGE_DEFAULT: int = 25
PAGE_MAX: int = 100

MONGO_CLIENT: Optional[AsyncMongoClient] = None
DB = None
COL = None


# ----------------------------------------------------
# DB dependency using AsyncMongoClient
# ----------------------------------------------------
async def get_db():
    global MONGO_CLIENT, DB, COL

    if MONGO_CLIENT is None:
        MONGO_CLIENT = AsyncMongoClient(mongoDb_uri)
        await MONGO_CLIENT.aconnect()

        DB = MONGO_CLIENT[DB_NAME]
        COL = DB[COLLECTION_NAME]

        # indexes
        await COL.create_index("id", unique=True)
        # await COL.create_index("category")
        # await COL.create_index("metadata.tags")
        await COL.create_index(
            [("metadata.priority", DESCENDING), ("metadata.last_updated", DESCENDING)]
        )

    return COL


# ----------------------------------------------------
# Router
# ----------------------------------------------------
router = APIRouter(prefix="/faqs", tags=["faqs"])


# -------------------- CREATE ------------------------
@router.post("/", response_model=FAQOutModel, status_code=201)
async def create_faq(FAQ: FAQCreateModel, COL=Depends(get_db)):
    FAQ_DICT = FAQ.model_dump()
    await COL.insert_one(FAQ_DICT)
    return FAQ_DICT


# -------------------- LIST / SEARCH -----------------
@router.get("/", response_model=List[FAQOutModel])
async def list_faqs(
    q: Optional[str] = Query(None),
    category: Optional[str] = None,
    tag: Optional[str] = None,
    visible: Optional[bool] = None,
    sort_by: str = Query("metadata.priority"),
    sort_order: int = Query(-1),
    page: int = Query(1, ge=1),
    page_size: int = Query(PAGE_DEFAULT, le=PAGE_MAX),
    COL=Depends(get_db),
):
    FILTER: Dict[str, Any] = {}

    if q:
        FILTER["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"data": {"$regex": q, "$options": "i"}},
        ]
    if category:
        FILTER["category"] = category
    if tag:
        FILTER["metadata.tags"] = tag
    if visible is not None:
        FILTER["metadata.visible"] = visible

    SKIP = (page - 1) * page_size

    CURSOR = COL.find(FILTER).sort(sort_by, sort_order).skip(SKIP).limit(page_size)

    RESULTS = [doc async for doc in CURSOR]
    return RESULTS


# -------------------- GET SINGLE FAQ -----------------
@router.get("/{FAQ_ID}", response_model=FAQOutModel)
async def get_faq(FAQ_ID: str, COL=Depends(get_db)):
    DOC = await COL.find_one({"id": FAQ_ID})
    if not DOC:
        raise HTTPException(404, "FAQ not found")
    return DOC


# -------------------- UPDATE (PUT) -------------------
@router.put("/{FAQ_ID}", response_model=FAQOutModel)
async def replace_faq(FAQ_ID: str, FAQ: FAQCreateModel, COL=Depends(get_db)):
    FAQ_DICT = FAQ.dict()
    FAQ_DICT["id"] = FAQ_ID
    FAQ_DICT["metadata"].last_updated = datetime.utcnow()

    await COL.replace_one({"id": FAQ_ID}, FAQ_DICT, upsert=True)
    return await COL.find_one({"id": FAQ_ID})


# -------------------- PATCH (partial update) --------
@router.patch("/{FAQ_ID}", response_model=FAQOutModel)
async def update_faq(FAQ_ID: str, BODY: FAQUpdateModel, COL=Depends(get_db)):
    UPDATE_DATA = BODY.dict(exclude_unset=True)

    SET_FIELDS = {}

    if "metadata" in UPDATE_DATA:
        META = UPDATE_DATA.pop("metadata")
        for K, V in META.items():
            SET_FIELDS[f"metadata.{K}"] = V

    for K, V in UPDATE_DATA.items():
        SET_FIELDS[K] = V

    SET_FIELDS["metadata.last_updated"] = datetime.utcnow()

    RESULT = await COL.find_one_and_update(
        {"id": FAQ_ID}, {"$set": SET_FIELDS}, return_document=True
    )

    if not RESULT:
        raise HTTPException(404, "FAQ not found")

    return RESULT


# -------------------- DELETE -------------------------
@router.delete("/{FAQ_ID}", status_code=204)
async def delete_faq(FAQ_ID: str, COL=Depends(get_db)):
    RES = await COL.delete_one({"id": FAQ_ID})
    if RES.deleted_count == 0:
        raise HTTPException(404, "FAQ not found")
    return JSONResponse(status_code=204, content=None)


# ----------------------------------------------------
# App wrapper for standalone run
# ----------------------------------------------------


if __name__ == "__main__":

    def create_app():
        APP = FastAPI(title="FAQ Service (AsyncMongoClient)")
        APP.include_router(router)
        return APP

    APP = create_app()
