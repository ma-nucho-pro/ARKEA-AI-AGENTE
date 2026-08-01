from fastapi import APIRouter
from pydantic import BaseModel
from backend.arkea_core.docs import create_docx, create_xlsx, create_pptx
from pathlib import Path

router = APIRouter(prefix="/api/arkea/docs", tags=["docs"])

class DocIn(BaseModel):
    title: str
    paragraphs: list[str] = []

class PptIn(BaseModel):
    title: str
    slides: list[dict] = []

@router.post("/docx")
def docx(body: DocIn):
    path = create_docx(body.title, body.paragraphs)
    return {"path": path, "download_url": "/data/generated/docs/" + Path(path).name}

@router.post("/pptx")
def pptx(body: PptIn):
    path = create_pptx(body.title, body.slides)
    return {"path": path, "download_url": "/data/generated/docs/" + Path(path).name}
