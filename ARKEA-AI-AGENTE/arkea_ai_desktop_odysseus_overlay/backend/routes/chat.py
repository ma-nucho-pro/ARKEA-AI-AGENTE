from fastapi import APIRouter
from pydantic import BaseModel
import traceback
from backend.arkea_core.agent import handle_message

router = APIRouter(prefix="/api/arkea", tags=["chat"])

class ChatIn(BaseModel):
    message: str
    project_id: int | None = None
    skill_id: str | None = None
    conversation_id: int | None = None
    mode: str = "auto"

@router.post("/chat")
def chat(body: ChatIn):
    try:
        return handle_message(body.message, body.project_id, body.skill_id, body.mode, body.conversation_id)
    except Exception as e:
        return {"ok": False, "say": "No pude completar esa acción por un error interno controlado. Intenta con una API recomendada o revisa Diagnóstico.", "error": str(e)[:500], "trace_tail": traceback.format_exc()[-3000:], "html_content": "<!doctype html><html><body style='font-family:Segoe UI,Arial;background:#071812;color:#effff5;padding:30px'><h1>ARKEA AI</h1><p>No pude completar esa acción por un error interno controlado.</p></body></html>"}
