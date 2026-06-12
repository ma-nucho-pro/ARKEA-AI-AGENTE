from fastapi import APIRouter
from pydantic import BaseModel
from backend.arkea_core.obsidian import configure_vault, write_note, get_vault

router = APIRouter(prefix="/api/arkea/obsidian", tags=["obsidian"])

class VaultIn(BaseModel):
    path: str

class NoteIn(BaseModel):
    section: str = "00_Global"
    title: str
    content: str

@router.get("/vault")
def vault():
    return {"vault": str(get_vault())}

@router.post("/configure")
def configure(body: VaultIn):
    return {"vault": configure_vault(body.path)}

@router.post("/note")
def note(body: NoteIn):
    return {"path": write_note(body.section, body.title, body.content)}
