import json
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from backend.arkea_core.db import execute, rows, one
from backend.arkea_core.mcp_runtime import (
    MCPConfirmationRequired,
    MCPRuntimeError,
    list_tools,
    call_tool,
)

router = APIRouter(prefix="/api/arkea/mcp", tags=["mcp-hub"])

class MCPIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    command: str = Field(min_length=1, max_length=1_000)
    args: list[str] = Field(default_factory=list, max_length=80)
    permissions: list[
        Literal["read", "write", "network", "execute", "browser", "filesystem"]
    ] = Field(min_length=1, max_length=6)
    requires_confirmation: bool = True

    @field_validator("permissions")
    @classmethod
    def require_execute_permission(cls, value):
        if "execute" not in value:
            raise ValueError("Todo servidor MCP requiere el permiso execute")
        return value


class MCPToolCall(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    arguments: dict = Field(default_factory=dict)
    confirmed: bool = False
    timeout_seconds: int = Field(default=45, ge=2, le=120)

@router.get("")
def list_mcp():
    return {"mcp_servers": rows("SELECT * FROM mcp_servers ORDER BY created_at DESC")}

@router.post("/add")
def add_mcp(body: MCPIn):
    mid = execute("INSERT INTO mcp_servers(name,command,args,permissions,requires_confirmation) VALUES(?,?,?,?,?)",
                  (body.name, body.command, json.dumps(body.args), json.dumps(body.permissions), int(body.requires_confirmation)))
    return {"id": mid, "ok": True}


@router.post("/{server_id}/toggle")
def toggle_mcp(server_id: int):
    server = one("SELECT enabled FROM mcp_servers WHERE id=?", (server_id,))
    if not server:
        raise HTTPException(404, "Servidor MCP no encontrado")
    enabled = 0 if server.get("enabled") else 1
    execute("UPDATE mcp_servers SET enabled=? WHERE id=?", (enabled, server_id))
    return {"ok": True, "enabled": bool(enabled)}


@router.get("/{server_id}/tools")
def tools(server_id: int):
    try:
        return {"ok": True, "tools": list_tools(server_id)}
    except MCPRuntimeError as exc:
        raise HTTPException(502, str(exc))


@router.post("/{server_id}/call")
def invoke_tool(server_id: int, body: MCPToolCall):
    try:
        return {
            "ok": True,
            "result": call_tool(
                server_id,
                body.name,
                body.arguments,
                confirmed=body.confirmed,
                timeout_seconds=body.timeout_seconds,
            ),
        }
    except MCPConfirmationRequired as exc:
        raise HTTPException(409, str(exc))
    except MCPRuntimeError as exc:
        raise HTTPException(502, str(exc))
