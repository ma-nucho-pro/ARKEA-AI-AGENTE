"""Shared agent context for every ARKEA capability.

The deterministic dispatcher remains in charge of filesystem and UI actions.
This module adds the same selected skill and tool catalogue to every model call,
regardless of whether the request creates chat, code, documents, vision, or web
content.
"""

from contextvars import ContextVar
from contextlib import contextmanager
import hashlib
import json
import re

from backend.arkea_core.db import get_setting, rows


_active_skill_id: ContextVar[str] = ContextVar("arkea_active_skill_id", default="")
_mcp_tool_aliases: ContextVar[dict[str, tuple[int, str]] | None] = ContextVar(
    "arkea_mcp_tool_aliases",
    default=None,
)

BUILTIN_TOOLS = (
    "create_project",
    "write_project_file",
    "preview_file",
    "create_docx",
    "create_xlsx",
    "create_pptx",
    "generate_image",
    "analyze_image",
    "research_web",
    "save_memory",
    "read_uploaded_files",
)


@contextmanager
def agent_request_context(skill_id: str | None = None):
    selected = (skill_id or get_setting("active_skill_id", "") or "").strip()
    token = _active_skill_id.set(selected)
    try:
        yield selected
    finally:
        _active_skill_id.reset(token)


def active_skill_id() -> str:
    return _active_skill_id.get()


def _skill_context(max_chars: int = 8_000) -> str:
    selected = active_skill_id()
    if not selected:
        return ""
    skill_rows = rows(
        "SELECT skill_id,name,description,folder_path,permissions FROM skills "
        "WHERE enabled=1 AND skill_id=? LIMIT 1",
        (selected,),
    )
    if not skill_rows:
        return ""
    skill = skill_rows[0]
    markdown = ""
    try:
        from pathlib import Path

        skill_path = Path(skill["folder_path"]) / "skill.md"
        if skill_path.is_file():
            markdown = skill_path.read_text(encoding="utf-8")[:max_chars]
    except Exception:
        markdown = ""
    permissions = skill.get("permissions") or "[]"
    return (
        f"\n\nSKILL ACTIVA PARA TODA LA INFRAESTRUCTURA\n"
        f"Nombre: {skill.get('name') or selected}\n"
        f"Permisos declarados: {permissions}\n"
        f"Instrucciones:\n{markdown}"
    )


def _tool_context(max_items: int = 30) -> str:
    external = rows(
        "SELECT name,command,args,permissions,requires_confirmation FROM mcp_servers "
        "WHERE enabled=1 ORDER BY created_at DESC LIMIT ?",
        (max_items,),
    )
    registered = []
    for item in external:
        try:
            permissions = json.loads(item.get("permissions") or "[]")
        except Exception:
            permissions = []
        registered.append(
            {
                "name": item.get("name"),
                "transport": "mcp",
                "permissions": permissions,
                "requires_confirmation": bool(item.get("requires_confirmation")),
            }
        )
    return (
        "\n\nHERRAMIENTAS DISPONIBLES\n"
        f"Integradas y ejecutables por ARKEA: {', '.join(BUILTIN_TOOLS)}.\n"
        f"MCP conectados (requieren el permiso indicado y, por defecto, confirmación): "
        f"{json.dumps(registered, ensure_ascii=False)}.\n"
        "Nunca afirmes que una herramienta externa se ejecutó si ARKEA no devuelve "
        "un resultado real de esa herramienta."
    )


def model_mcp_tools(max_servers: int = 8, max_tools: int = 40) -> list[dict]:
    """Return executable OpenAI-compatible tools for explicitly autonomous MCPs."""
    from backend.arkea_core.mcp_runtime import list_tools

    servers = rows(
        "SELECT id,name,permissions FROM mcp_servers "
        "WHERE enabled=1 AND requires_confirmation=0 ORDER BY created_at DESC LIMIT ?",
        (max_servers,),
    )
    aliases: dict[str, tuple[int, str]] = {}
    result: list[dict] = []
    for server in servers:
        try:
            tools = list_tools(int(server["id"]), timeout_seconds=15)
        except Exception:
            continue
        for tool in tools:
            original = str(tool.get("name") or "").strip()
            if not original:
                continue
            server_id = int(server["id"])
            safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", original) or "tool"
            digest = hashlib.sha256(
                f"{server_id}\0{original}".encode("utf-8")
            ).hexdigest()[:10]
            prefix = f"mcp_{server_id}_"
            safe_limit = max(1, 64 - len(prefix) - len(digest) - 1)
            alias = f"{prefix}{safe_name[:safe_limit]}_{digest}"
            if alias in aliases:
                continue
            aliases[alias] = (server_id, original)
            schema = tool.get("inputSchema") or tool.get("input_schema") or {"type": "object"}
            if not isinstance(schema, dict):
                schema = {"type": "object"}
            result.append(
                {
                    "type": "function",
                    "function": {
                        "name": alias,
                        "description": (
                            f"MCP {server.get('name')}: {tool.get('description') or original}. "
                            f"Permisos aplicados: {server.get('permissions') or '[]'}"
                        )[:900],
                        "parameters": schema,
                    },
                }
            )
            if len(result) >= max_tools:
                _mcp_tool_aliases.set(aliases)
                return result
    _mcp_tool_aliases.set(aliases)
    return result


def execute_mcp_model_tool(alias: str, arguments: dict) -> dict:
    from backend.arkea_core.mcp_runtime import call_tool

    target = (_mcp_tool_aliases.get() or {}).get(alias)
    if not target:
        raise ValueError("La herramienta MCP solicitada no está registrada")
    server_id, original_name = target
    return call_tool(server_id, original_name, arguments, confirmed=False)


def enrich_system_prompt(system: str, task: str = "chat") -> str:
    base = (system or "Eres ARKEA AI.").strip()
    policy = (
        f"\n\nCONTEXTO DEL AGENTE\nTarea actual: {task}. "
        "La misma política de skills, memoria y herramientas se aplica a chat, "
        "código, documentos, visión, búsqueda, imágenes y automatización. "
        "Las acciones sensibles o externas requieren confirmación explícita."
    )
    return (base + policy + _skill_context() + _tool_context())[:24_000]
