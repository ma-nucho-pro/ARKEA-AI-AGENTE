import json
from fastapi import APIRouter
from pydantic import BaseModel
from backend.arkea_core.db import execute, rows

router = APIRouter(prefix="/api/arkea/mcp", tags=["mcp-hub"])

class MCPIn(BaseModel):
    name: str
    command: str
    args: list[str] = []
    permissions: list[str] = []
    requires_confirmation: bool = True

@router.get("")
def list_mcp():
    return {"mcp_servers": rows("SELECT * FROM mcp_servers ORDER BY created_at DESC")}

@router.post("/add")
def add_mcp(body: MCPIn):
    mid = execute("INSERT INTO mcp_servers(name,command,args,permissions,requires_confirmation) VALUES(?,?,?,?,?)",
                  (body.name, body.command, json.dumps(body.args), json.dumps(body.permissions), int(body.requires_confirmation)))
    return {"id": mid, "ok": True}
