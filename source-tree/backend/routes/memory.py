from fastapi import APIRouter
from pydantic import BaseModel
from backend.arkea_core.memory import save_memory, list_memory, archive_memory

router = APIRouter(prefix="/api/arkea/memory", tags=["memory"])

class MemoryIn(BaseModel):
    scope: str = "global"
    scope_id: str = ""
    title: str = ""
    content: str
    tags: str = ""
    source: str = "manual"
    importance: int = 1

@router.get("")
def get(scope: str | None = None, scope_id: str | None = None):
    return {"memories": list_memory(scope, scope_id)}

@router.post("/save")
def save(body: MemoryIn):
    return {"id": save_memory(body.scope, body.content, body.title, body.scope_id, body.tags, body.source, body.importance)}

@router.post("/{memory_id}/archive")
def archive(memory_id: int):
    archive_memory(memory_id)
    return {"ok": True}
