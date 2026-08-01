from fastapi import APIRouter
from typing import Literal
from pydantic import BaseModel, Field
from backend.arkea_core.obsidian import configure_vault, write_note, get_vault

router = APIRouter(prefix="/api/arkea/obsidian", tags=["obsidian"])

class VaultIn(BaseModel):
    path: str = Field(min_length=1, max_length=1_000)

class NoteIn(BaseModel):
    section: Literal[
        "00_Global", "01_Projects", "02_Skills", "03_Research",
        "04_Generated", "05_History",
    ] = "00_Global"
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=2_000_000)

@router.get("/vault")
def vault():
    return {"vault": str(get_vault())}

@router.post("/configure")
def configure(body: VaultIn):
    return {"vault": configure_vault(body.path)}

@router.post("/note")
def note(body: NoteIn):
    return {"path": write_note(body.section, body.title, body.content)}
