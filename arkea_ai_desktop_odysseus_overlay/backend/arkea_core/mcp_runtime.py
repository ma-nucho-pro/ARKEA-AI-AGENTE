"""Small, bounded MCP stdio client used by ARKEA.

Each operation starts a fresh server process, performs the JSON-RPC handshake,
executes one bounded operation, and terminates the process tree. Commands are
passed as argv with shell=False; no command string is evaluated by a shell.
"""

import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from typing import Any

from backend.arkea_core.db import execute, one


ALLOWED_COMMAND_NAMES = {
    "node", "node.exe", "npx", "npx.cmd", "python", "python.exe",
    "py", "py.exe", "uvx", "uvx.exe",
}
MAX_RPC_BYTES = 2 * 1024 * 1024
MAX_TOOL_INPUT_BYTES = 1024 * 1024
MAX_ARGUMENTS = 80
ALLOWED_PERMISSIONS = {"read", "write", "network", "execute", "browser", "filesystem"}


class MCPRuntimeError(RuntimeError):
    pass


class MCPConfirmationRequired(MCPRuntimeError):
    pass


class MCPPermissionDenied(MCPRuntimeError):
    pass


def _server(server_id: int) -> dict:
    row = one("SELECT * FROM mcp_servers WHERE id=? AND enabled=1", (server_id,))
    if not row:
        raise MCPRuntimeError("Servidor MCP no encontrado o desactivado")
    return row


def _decode_args(value: str | None) -> list[str]:
    try:
        args = json.loads(value or "[]")
    except Exception as exc:
        raise MCPRuntimeError("Los argumentos MCP guardados no son JSON válido") from exc
    if not isinstance(args, list) or len(args) > MAX_ARGUMENTS:
        raise MCPRuntimeError("Lista de argumentos MCP no válida")
    result = []
    for arg in args:
        text = str(arg)
        if "\x00" in text or len(text) > 4_000:
            raise MCPRuntimeError("Argumento MCP no permitido")
        result.append(text)
    return result


def _validated_command(value: str) -> str:
    command = str(value or "").strip().strip('"')
    if not command or any(ch in command for ch in "\r\n\x00"):
        raise MCPRuntimeError("Comando MCP no válido")
    candidate = Path(command)
    name = candidate.name.lower()
    if name in ALLOWED_COMMAND_NAMES:
        return command
    if candidate.is_absolute() and candidate.is_file() and candidate.suffix.lower() == ".exe":
        return str(candidate.resolve())
    raise MCPRuntimeError(
        "Comando MCP bloqueado. Usa node, npx, Python, uvx o una ruta absoluta a un .exe."
    )


def _minimal_env() -> dict[str, str]:
    allowed = (
        "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "TEMP", "TMP",
        "USERPROFILE", "HOME", "LOCALAPPDATA", "APPDATA", "PROGRAMFILES",
    )
    return {key: value for key, value in os.environ.items() if key.upper() in allowed}


def _parse_messages(raw: bytes) -> list[dict]:
    if len(raw) > MAX_RPC_BYTES:
        raise MCPRuntimeError("La respuesta MCP superó el límite permitido")
    text = raw.decode("utf-8", errors="replace")
    messages: list[dict] = []
    # JSON Lines transport.
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                messages.append(item)
        except Exception:
            continue
    if messages:
        return messages
    # Compatibility with older Content-Length framed stdio servers.
    pattern = re.compile(br"Content-Length:\s*(\d+)\r?\n\r?\n", re.I)
    pos = 0
    while True:
        match = pattern.search(raw, pos)
        if not match:
            break
        length = int(match.group(1))
        start = match.end()
        payload = raw[start:start + length]
        pos = start + length
        try:
            item = json.loads(payload.decode("utf-8"))
            if isinstance(item, dict):
                messages.append(item)
        except Exception:
            continue
    return messages


def _kill_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
                check=False,
            )
            return
        except Exception:
            pass
    try:
        process.kill()
    except Exception:
        pass


def _server_permissions(server: dict) -> set[str]:
    try:
        values = json.loads(server.get("permissions") or "[]")
    except Exception as exc:
        raise MCPPermissionDenied("Los permisos MCP guardados no son válidos") from exc
    if not isinstance(values, list):
        raise MCPPermissionDenied("Los permisos MCP guardados no son válidos")
    normalized = {str(item).strip().lower() for item in values}
    if not normalized or not normalized.issubset(ALLOWED_PERMISSIONS):
        raise MCPPermissionDenied("El servidor MCP no tiene una política de permisos válida")
    return normalized


def _required_permissions(tool_name: str, arguments: dict[str, Any]) -> set[str]:
    name = tool_name.lower()
    # Toda tool MCP inicia código externo. Los demás permisos describen la
    # intención de la operación y no sustituyen este permiso base.
    required = {"execute"}
    if any(word in name for word in (
        "delete", "remove", "write", "create", "update", "edit", "move",
        "copy", "mkdir", "save", "upload", "append", "rename", "download",
    )):
        required.add("write")
    if any(word in name for word in (
        "read", "list", "search", "find", "get", "stat", "open", "load",
        "download", "upload", "copy", "move",
    )):
        required.add("read")
    if any(word in name for word in (
        "http", "fetch", "request", "web", "url", "browser", "download", "upload",
    )):
        required.add("network")
    if "browser" in name:
        required.add("browser")
    if any(word in name for word in (
        "file", "path", "folder", "directory", "filesystem", "fs_",
    )):
        required.add("filesystem")
    keys = {str(key).lower() for key in arguments}
    if keys.intersection({"path", "file", "filename", "directory", "folder", "root"}):
        required.add("filesystem")
    if keys.intersection({"url", "uri", "endpoint", "host"}):
        required.add("network")
    return required


def _enforce_permissions(server: dict, tool_name: str, arguments: dict[str, Any]) -> None:
    missing = _required_permissions(tool_name, arguments) - _server_permissions(server)
    if missing:
        raise MCPPermissionDenied(
            "Permiso MCP denegado; faltan: " + ", ".join(sorted(missing))
        )


def _bounded_communicate(
    process: subprocess.Popen, stdin_data: bytes, timeout_seconds: int
) -> tuple[bytes, bytes]:
    buffers: list[list[bytes]] = [[], []]
    sizes = [0, 0]
    overflow = threading.Event()

    def read_stream(index: int, stream) -> None:
        while True:
            chunk = stream.read(64 * 1024)
            if not chunk:
                return
            sizes[index] += len(chunk)
            if sizes[index] > MAX_RPC_BYTES:
                overflow.set()
                _kill_process_tree(process)
                return
            buffers[index].append(chunk)

    readers = [
        threading.Thread(target=read_stream, args=(0, process.stdout), daemon=True),
        threading.Thread(target=read_stream, args=(1, process.stderr), daemon=True),
    ]
    for reader in readers:
        reader.start()
    try:
        if process.stdin is not None:
            process.stdin.write(stdin_data)
            process.stdin.close()
    except BrokenPipeError:
        pass
    started = time.monotonic()
    while process.poll() is None:
        if overflow.is_set():
            _kill_process_tree(process)
            break
        if time.monotonic() - started > timeout_seconds:
            _kill_process_tree(process)
            raise subprocess.TimeoutExpired(process.args, timeout_seconds)
        time.sleep(0.05)
    for reader in readers:
        reader.join(timeout=5)
    if overflow.is_set() or any(reader.is_alive() for reader in readers):
        _kill_process_tree(process)
        raise MCPRuntimeError("La salida del servidor MCP superó el límite permitido")
    return b"".join(buffers[0]), b"".join(buffers[1])


def _rpc(server: dict, method: str, params: dict | None = None,
         timeout_seconds: int = 30) -> dict:
    if "execute" not in _server_permissions(server):
        raise MCPPermissionDenied("Permiso MCP denegado; falta: execute")
    command = _validated_command(server.get("command") or "")
    args = _decode_args(server.get("args"))
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "ARKEA AI OmniAgent", "version": "0.1.0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": method, "params": params or {}},
    ]
    stdin_data = ("\n".join(json.dumps(item, ensure_ascii=False) for item in requests) + "\n").encode("utf-8")
    process = subprocess.Popen(
        [command, *args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        env=_minimal_env(),
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    try:
        stdout, stderr = _bounded_communicate(
            process, stdin_data, max(2, min(timeout_seconds, 120))
        )
    except subprocess.TimeoutExpired as exc:
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    shell=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    check=False,
                )
            except Exception:
                process.kill()
        else:
            process.kill()
        try:
            process.wait(timeout=5)
        except Exception:
            _kill_process_tree(process)
        raise MCPRuntimeError("El servidor MCP agotó el tiempo límite") from exc
    if len(stderr) > MAX_RPC_BYTES:
        stderr = stderr[:MAX_RPC_BYTES]
    messages = _parse_messages(stdout)
    response = next((item for item in messages if item.get("id") == 2), None)
    if not response:
        detail = stderr.decode("utf-8", errors="replace").strip()[:800]
        raise MCPRuntimeError(detail or f"El servidor MCP terminó con código {process.returncode}")
    if response.get("error"):
        raise MCPRuntimeError(json.dumps(response["error"], ensure_ascii=False)[:1_200])
    return response.get("result") or {}


def list_tools(server_id: int, timeout_seconds: int = 30) -> list[dict]:
    server = _server(server_id)
    result = _rpc(server, "tools/list", {}, timeout_seconds)
    tools = result.get("tools") or []
    return tools[:200] if isinstance(tools, list) else []


def call_tool(server_id: int, name: str, arguments: dict[str, Any],
              *, confirmed: bool = False, timeout_seconds: int = 45) -> dict:
    server = _server(server_id)
    if server.get("requires_confirmation") and not confirmed:
        raise MCPConfirmationRequired("Esta herramienta requiere confirmación explícita")
    if not name or len(name) > 200 or not isinstance(arguments, dict):
        raise MCPRuntimeError("Llamada de herramienta no válida")
    encoded_arguments = json.dumps(arguments, ensure_ascii=False)
    if len(encoded_arguments.encode("utf-8")) > MAX_TOOL_INPUT_BYTES:
        raise MCPRuntimeError("Los argumentos de la herramienta superan el límite permitido")
    _enforce_permissions(server, name, arguments)
    try:
        result = _rpc(
            server,
            "tools/call",
            {"name": name, "arguments": arguments},
            timeout_seconds,
        )
        execute(
            "INSERT INTO tool_events(tool_name,input_json,output_json,status) VALUES(?,?,?,?)",
            (
                f"mcp:{server.get('name')}:{name}",
                encoded_arguments[:20_000],
                json.dumps(result, ensure_ascii=False)[:40_000],
                "ok",
            ),
        )
        return result
    except Exception as exc:
        execute(
            "INSERT INTO tool_events(tool_name,input_json,output_json,status) VALUES(?,?,?,?)",
            (
                f"mcp:{server.get('name')}:{name}",
                encoded_arguments[:20_000],
                str(exc)[:4_000],
                "error",
            ),
        )
        raise
