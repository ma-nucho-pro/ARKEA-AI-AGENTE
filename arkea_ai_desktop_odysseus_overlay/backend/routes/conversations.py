from fastapi import APIRouter
from pydantic import BaseModel
from backend.arkea_core.conversations import create_conversation, list_conversations, set_active, get_messages

router = APIRouter(prefix="/api/arkea/conversations", tags=["conversations"])

class ConversationIn(BaseModel):
    title: str = 'Nuevo chat'
    project_id: int | None = None
    folder_path: str | None = None

@router.get("")
def get_all():
    return {"conversations": list_conversations()}

@router.post("/create")
def create(body: ConversationIn):
    return create_conversation(body.title, body.project_id, body.folder_path)

@router.get("/active-current")
def active_current():
    from backend.arkea_core.conversations import get_or_create_active
    c = get_or_create_active('Nuevo chat')
    return {"conversation": c, "messages": get_messages(c['id'])}

@router.post("/{conversation_id}/active")
def active(conversation_id: int):
    return set_active(conversation_id)

@router.get("/{conversation_id}/messages")
def messages(conversation_id: int):
    return {"messages": get_messages(conversation_id)}
