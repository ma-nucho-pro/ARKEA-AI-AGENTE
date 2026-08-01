from fastapi import APIRouter
from pydantic import BaseModel, Field
import traceback
from backend.arkea_core.agent import handle_message

router = APIRouter(prefix="/api/arkea", tags=["chat"])

class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=250_000)
    project_id: int | None = None
    skill_id: str | None = None
    conversation_id: int | None = None
    mode: str = Field(default="auto", max_length=30)

@router.post("/chat")
def chat(body: ChatIn):
    try:
        return handle_message(body.message, body.project_id, body.skill_id, body.mode, body.conversation_id)
    except Exception:
        traceback.print_exc()
        return {"ok": False, "say": "No pude completar esa acción por un error interno controlado. Intenta con una API recomendada o revisa Diagnóstico.", "html_content": "<!doctype html><html><body style='font-family:Segoe UI,Arial;background:#071812;color:#effff5;padding:30px'><h1>ARKEA AI</h1><p>No pude completar esa acción por un error interno controlado.</p></body></html>"}
