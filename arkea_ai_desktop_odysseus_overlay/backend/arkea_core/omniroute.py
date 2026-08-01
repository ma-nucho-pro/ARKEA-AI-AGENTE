"""OmniRoute sidecar integration for ARKEA AI.

OmniRoute is treated as an independent local gateway. ARKEA never copies or
modifies provider credentials managed by OmniRoute; it only talks to its
loopback OpenAI-compatible endpoint.
"""

import json
import os
from urllib.parse import urlsplit

from backend.arkea_core.db import execute, get_setting, rows, upsert_setting
from backend.arkea_core.security import guarded_request


DEFAULT_ORIGIN = os.getenv("OMNIROUTE_BASE_URL", "http://127.0.0.1:20128").rstrip("/")
CHAT_PATH = "/v1/chat/completions"
IMAGE_PATH = "/v1/images/generations"

TASK_MODELS = {
    "chat": "auto",
    "code": "auto/coding",
    "artifact": "auto/coding",
    "document": "auto",
    "file": "auto",
    "vision": "auto",
    "web_search": "auto",
    "image_generation": "auto",
}


def _origin(value: str | None = None) -> str:
    candidate = (value or get_setting("omniroute_base_url", DEFAULT_ORIGIN) or DEFAULT_ORIGIN).strip().rstrip("/")
    parsed = urlsplit(candidate)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "http" or hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("OmniRoute debe usar un endpoint HTTP de loopback")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("La URL de OmniRoute debe contener solo el origen local")
    if (parsed.port or 80) != 20128:
        raise ValueError("El puerto permitido para OmniRoute es 20128")
    return f"http://[{hostname}]:20128" if hostname == "::1" else f"http://{hostname}:20128"


def api_key() -> str:
    stored = (get_setting("omniroute_api_key", "") or "").strip()
    return stored or os.getenv("OMNIROUTE_API_KEY", "").strip()


def headers() -> dict[str, str]:
    result = {"Content-Type": "application/json"}
    key = api_key()
    if key:
        result["Authorization"] = f"Bearer {key}"
    return result


def status(timeout: float = 1.5) -> dict:
    origin = _origin()
    health_path = "/api/monitoring/health"
    try:
        health = guarded_request(
            "GET",
            origin + health_path,
            allow_local=True,
            headers=headers(),
            timeout=timeout,
            max_response_bytes=2 * 1024 * 1024,
        )
        health_data = health.json() if health.status_code == 200 else {}
        if (
            not isinstance(health_data, dict)
            or health_data.get("status") != "healthy"
            or health_data.get("version") != "3.8.48"
        ):
            raise RuntimeError("La identidad o versión de OmniRoute no coincide")
        model_response = guarded_request(
            "GET",
            origin + "/v1/models",
            allow_local=True,
            headers=headers(),
            timeout=timeout,
            max_response_bytes=2 * 1024 * 1024,
        )
        model_data = model_response.json() if model_response.status_code == 200 else {}
        models_value = model_data.get("data") if isinstance(model_data, dict) else None
        if model_response.status_code != 200 or not isinstance(models_value, list):
            raise RuntimeError(
                f"OmniRoute rechazó la comprobación autenticada ({model_response.status_code})"
            )
        return {
            "installed": True,
            "running": True,
            "status_code": 200,
            "base_url": origin,
            "model_count": len(models_value),
            "health_path": health_path,
            "version": "3.8.48",
            "authenticated": True,
        }
    except Exception as exc:
        last_error = str(exc)[:240]
    return {
        "installed": False,
        "running": False,
        "base_url": origin,
        "model_count": 0,
        "version": "3.8.48",
        "error": last_error or "OmniRoute no está iniciado",
    }


def models(timeout: float = 8.0) -> list[dict]:
    response = guarded_request(
        "GET",
        _origin() + "/v1/models",
        allow_local=True,
        headers=headers(),
        timeout=timeout,
        max_response_bytes=5 * 1024 * 1024,
    )
    response.raise_for_status()
    payload = response.json()
    return (payload.get("data") or [])[:500] if isinstance(payload, dict) else []


def configure(*, mode: str, base_url: str | None = None, key: str | None = None,
              models_by_task: dict | None = None) -> dict:
    allowed_modes = {"auto", "free", "local", "direct"}
    if mode not in allowed_modes:
        raise ValueError("Modo de IA no válido")
    origin = _origin(base_url)
    upsert_setting("ai_engine_mode", mode)
    upsert_setting("omniroute_base_url", origin)
    if key is not None and key.strip():
        upsert_setting("omniroute_api_key", key.strip())
    for task, model in (models_by_task or {}).items():
        if task in TASK_MODELS and isinstance(model, str) and 0 < len(model.strip()) <= 240:
            upsert_setting(f"omniroute_model_{task}", model.strip())
    return settings()


def settings() -> dict:
    configured_key = bool(api_key())
    return {
        "mode": get_setting("ai_engine_mode", "auto"),
        "base_url": _origin(),
        "api_key_configured": configured_key,
        "models": {
            task: get_setting(f"omniroute_model_{task}", default)
            for task, default in TASK_MODELS.items()
        },
        "last_decision": get_setting("omniroute_last_decision", ""),
    }


def connection_for(task: str) -> dict:
    api_type = "image_generation" if task in {"image", "image_generation"} else task
    endpoint = _origin() + (IMAGE_PATH if api_type == "image_generation" else CHAT_PATH)
    default_model = TASK_MODELS.get(api_type, TASK_MODELS["chat"])
    return {
        "api_type": api_type,
        "provider": "omniroute",
        "display_name": f"OmniRoute {api_type}",
        "base_url": endpoint,
        "api_key": api_key(),
        "model_id": get_setting(f"omniroute_model_{api_type}", default_model),
        "extra_json": json.dumps(
            {"max_tokens": 4500 if api_type in {"code", "artifact", "document"} else 2200},
            ensure_ascii=False,
        ),
        "enabled": 1,
    }


def apply_connections() -> dict:
    created = 0
    updated = 0
    for task in TASK_MODELS:
        item = connection_for(task)
        existing = rows(
            "SELECT id,api_key FROM api_connections "
            "WHERE api_type=? AND provider='omniroute' AND display_name=? LIMIT 1",
            (item["api_type"], item["display_name"]),
        )
        if existing:
            current_key = existing[0].get("api_key") or ""
            new_key = item["api_key"] or current_key
            execute(
                "UPDATE api_connections SET base_url=?,api_key=?,model_id=?,extra_json=?,"
                "enabled=1,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (item["base_url"], new_key, item["model_id"], item["extra_json"], existing[0]["id"]),
            )
            updated += 1
        else:
            execute(
                "INSERT INTO api_connections(api_type,provider,display_name,base_url,api_key,"
                "model_id,extra_json,enabled) VALUES(?,?,?,?,?,?,?,1)",
                (
                    item["api_type"],
                    item["provider"],
                    item["display_name"],
                    item["base_url"],
                    item["api_key"],
                    item["model_id"],
                    item["extra_json"],
                ),
            )
            created += 1
    return {"ok": True, "created": created, "updated": updated, "total": created + updated}


def remember_decision(value: str) -> None:
    if value:
        upsert_setting("omniroute_last_decision", str(value)[:500])
