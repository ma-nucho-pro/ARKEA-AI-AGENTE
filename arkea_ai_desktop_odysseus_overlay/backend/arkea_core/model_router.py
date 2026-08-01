import json, re
from backend.arkea_core.security import guarded_request
from backend.arkea_core.db import rows, get_setting, execute
from backend.arkea_core.ollama import chat_local
from backend.arkea_core.agent_runtime import (
    enrich_system_prompt,
    execute_mcp_model_tool,
    model_mcp_tools,
)
from backend.arkea_core import omniroute

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

TASK_PRIORITY = {
    "vision": ["vision", "chat"],
    "web": ["web_search", "chat"],
    "file": ["file", "vision", "chat"],
    "code": ["code", "artifact", "chat"],
    "artifact": ["artifact", "code", "chat"],
    "document": ["document", "artifact", "file", "chat"],
    "image": ["image_generation", "image"],
    "chat": ["chat"],
}

def _j(v):
    try:
        return json.loads(v or "{}")
    except Exception:
        return {}

def _bad_api(api):
    model = (api.get("model_id") or "").strip()
    provider = (api.get("provider") or "").lower()
    base = (api.get("base_url") or "").lower()
    key = (api.get("api_key") or "").strip()
    if model in ("google/gemini-2.5-flash:free", "xiaomi/mimo-flash:free", "openai/gpt-4o-mini"):
        return True
    if ("openrouter" in provider or "openrouter.ai" in base) and len(key) < 20:
        return True
    return False

def _enabled_candidates(task: str):
    types = TASK_PRIORITY.get(task, ["chat"])
    out = []
    for t in types:
        out += rows("SELECT * FROM api_connections WHERE enabled=1 AND api_type=? ORDER BY updated_at DESC, id DESC", (t,))
    # fallback: any OpenRouter chat
    if not out and task != "chat":
        out += rows("SELECT * FROM api_connections WHERE enabled=1 AND provider LIKE '%openrouter%' ORDER BY updated_at DESC, id DESC")
    out = [a for a in out if not _bad_api(a)]
    mode = (get_setting("ai_engine_mode", "auto") or "auto").strip().lower()
    if mode in {"auto", "free"} and task not in {"image", "image_generation"}:
        omni_task = "web_search" if task == "web" else task
        synthetic = omniroute.connection_for(omni_task)
        duplicate = any(
            (item.get("provider") or "").lower() == "omniroute"
            and (item.get("api_type") or "") == synthetic["api_type"]
            for item in out
        )
        if not duplicate:
            out.insert(0, synthetic)
    if mode == "free":
        return [a for a in out if "omniroute" in (a.get("provider") or "").lower()]
    if mode == "direct":
        return [a for a in out if _is_direct_provider(a)]
    return out


def _is_direct_provider(api: dict) -> bool:
    provider = (api.get("provider") or "").strip().lower()
    base_url = (api.get("base_url") or "").strip().lower()
    local_names = {
        "omniroute", "ollama", "ollama_local", "ollama_vision",
        "comfyui_local", "automatic1111_local", "local_whisper",
    }
    if provider in local_names or provider.startswith("ollama") or provider.endswith("_local"):
        return False
    return not any(
        marker in base_url
        for marker in ("127.0.0.1", "localhost", "[::1]", "0.0.0.0")
    )

def _score(api, task):
    provider = (api.get("provider") or "").lower()
    model = (api.get("model_id") or "").lower()
    score = 0
    mode = (get_setting("ai_engine_mode", "auto") or "auto").strip().lower()
    if "omniroute" in provider:
        score += 500 if mode in {"auto", "free"} else 20
    if "openrouter/free" in model: score += 65
    if "free" in model or "free" in provider: score += 50
    if task in ("artifact","code","document") and "qwen3-coder" in model: score += 55
    if task in ("artifact","code","document","chat") and "deepseek-v4-flash" in model: score += 50
    if task == "vision" and any(x in model for x in ["nex-n2-pro:free", "step-3.7-flash", "qwen3.7-plus", "minimax-m3"]): score += 60
    if task == "vision" and any(x in model for x in ["mimo-v2.5", "step-3.7-flash"]): score += 40
    if task == "web" and "openrouter/auto" in model: score += 60
    if task == "file" and "openrouter/auto" in model: score += 50
    if task == "chat" and "deepseek-v4-flash" in model: score += 40
    if "openrouter" in provider or "openrouter" in (api.get("base_url") or ""): score += 10
    return score

def pick_api(task: str):
    candidates = _enabled_candidates(task)
    if not candidates:
        return None
    return sorted(candidates, key=lambda a: _score(a, task), reverse=True)[0]

def ranked_apis(task: str):
    return sorted(_enabled_candidates(task), key=lambda a: _score(a, task), reverse=True)

def _headers(api):
    key = api.get("api_key") or ""
    extra = _j(api.get("extra_json"))
    h = {"Content-Type":"application/json"}
    if key:
        h["Authorization"] = f"Bearer {key}"
    if "openrouter" in (api.get("provider") or "").lower() or "openrouter" in (api.get("base_url") or ""):
        h["HTTP-Referer"] = extra.get("site_url") or get_setting("site_url", "http://127.0.0.1")
        h["X-Title"] = "ARKEA AI"
    for k,v in (extra.get("headers") or {}).items():
        h[str(k)] = str(v)
    return h

def _extract_content(data):
    try:
        msg = data.get("choices", [{}])[0].get("message", {})
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            return content
        reasoning = msg.get("reasoning") or ""
        if reasoning:
            # No mostrar JSON ni cadena de pensamiento. Devolver resumen corto utilizable.
            return re.sub(r"\s+", " ", str(reasoning)).strip()[:700]
    except Exception:
        pass
    return data.get("text") or data.get("output_text") or json.dumps(data, ensure_ascii=False)[:1200]

def _normalized_chat_url(value: str) -> str:
    url = (value or "").strip().rstrip("/")
    if url.endswith("/v1"):
        return url + "/chat/completions"
    return url

def _route_candidate(api: dict, message: str, task: str, system: str,
                     max_tokens: int | None, timeout_ms: int | None):
    extra = _j(api.get("extra_json"))
    base_url = _normalized_chat_url(api.get("base_url") or OPENROUTER_URL)
    model = api.get("model_id") or ("openrouter/auto" if task in ("web","file") else "deepseek/deepseek-v4-flash")
    mt = max_tokens or int(extra.get("max_tokens") or (4500 if task in ("artifact","code") else 2200))
    timeout = (timeout_ms or int(extra.get("stream_timeout_ms") or 75000)) / 1000
    messages = [
        {"role":"system","content": system},
        {"role":"user","content": message}
    ]
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": mt,
        "temperature": 0.25
    }
    if task == "web" or extra.get("web_search"):
        payload["web_search_options"] = {"search_context_size":"medium"}
    provider = (api.get("provider") or "").lower()
    if provider.startswith("ollama"):
        return chat_local(message, system=system), model, "ollama"
    mcp_tools = model_mcp_tools()
    if mcp_tools:
        payload["tools"] = mcp_tools
        payload["tool_choice"] = "auto"
    allow_local = provider in (
        "omniroute", "ollama_local", "ollama_vision", "comfyui_local",
        "automatic1111_local", "local_whisper"
    )
    response = guarded_request(
        "POST", base_url, allow_local=allow_local, headers=_headers(api),
        json=payload, timeout=timeout
    )
    response.raise_for_status()
    response_data = response.json()
    try:
        assistant_message = response_data.get("choices", [{}])[0].get("message", {})
        tool_calls = assistant_message.get("tool_calls") or []
    except Exception:
        assistant_message, tool_calls = {}, []
    if tool_calls:
        followup_messages = [
            *messages,
            {
                "role": "assistant",
                "content": assistant_message.get("content") or "",
                "tool_calls": tool_calls[:4],
            },
        ]
        for call in tool_calls[:4]:
            function = call.get("function") or {}
            alias = str(function.get("name") or "")
            try:
                arguments = json.loads(function.get("arguments") or "{}")
                if not isinstance(arguments, dict):
                    raise ValueError("Los argumentos MCP deben ser un objeto")
                tool_result = execute_mcp_model_tool(alias, arguments)
                content = json.dumps(tool_result, ensure_ascii=False)[:20_000]
            except Exception as exc:
                content = json.dumps({"error": str(exc)[:1_000]}, ensure_ascii=False)
            followup_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": str(call.get("id") or alias),
                    "name": alias,
                    "content": content,
                }
            )
        followup_payload = {
            **payload,
            "messages": followup_messages,
        }
        followup_payload.pop("tools", None)
        followup_payload.pop("tool_choice", None)
        response = guarded_request(
            "POST", base_url, allow_local=allow_local, headers=_headers(api),
            json=followup_payload, timeout=timeout
        )
        response.raise_for_status()
        response_data = response.json()
    text = _extract_content(response_data).strip()
    if not text:
        raise ValueError("El proveedor no devolvió texto")
    decision = response.headers.get("X-OmniRoute-Decision", "")
    if "omniroute" in provider:
        omniroute.remember_decision(decision or f"model={model}")
    try:
        execute(
            "INSERT INTO app_events(event_type,payload) VALUES(?,?)",
            ("model_route", json.dumps({
                "task": task, "provider": provider, "model": model,
                "decision": decision[:500],
            }, ensure_ascii=False)),
        )
    except Exception:
        pass
    return text, model, decision or provider

def route_text(message: str, task: str = "chat", system: str = "", max_tokens: int | None = None, timeout_ms: int | None = None):
    system_prompt = enrich_system_prompt(system or ARKEA_AGENT_SYSTEM, task)
    mode = (get_setting("ai_engine_mode", "auto") or "auto").strip().lower()
    if mode not in {"auto", "free", "local", "direct"}:
        mode = "auto"
    if mode == "local":
        local = chat_local(message, system=system_prompt)
        return local or "Ollama local no está disponible. Inícialo o cambia el motor en Ajustes > IA universal."
    errors = []
    for api in ranked_apis(task):
        try:
            text, _model, _decision = _route_candidate(
                api, message, task, system_prompt, max_tokens, timeout_ms
            )
            if text:
                return text
        except Exception as exc:
            errors.append(str(exc)[:180])
            continue
    if mode == "free":
        detail = f" Detalle: {errors[-1]}" if errors else ""
        return (
            "OmniRoute gratuito no está disponible. No se usó ninguna API directa ni Ollama "
            f"porque el modo Gratis es estricto.{detail}"
        )
    if mode == "direct":
        detail = f" Detalle: {errors[-1]}" if errors else ""
        return (
            "Ninguna API directa configurada respondió. No se cambió silenciosamente a "
            f"OmniRoute ni a Ollama.{detail}"
        )
    # Modo automático: OmniRoute y las conexiones configuradas ya se intentaron
    # por puntuación; Ollama es el último recurso local y visible.
    fallback = chat_local(message, system=system_prompt)
    if fallback:
        try:
            omniroute.remember_decision("fallback=ollama;reason=providers_unavailable")
        except Exception:
            pass
        return fallback
    detail = f" Detalle: {errors[-1]}" if errors else ""
    return f"No hay un motor de IA disponible. Revisa Ajustes > IA universal.{detail}"

def route_html(prompt: str):
    system = ARKEA_AGENT_SYSTEM + "\nDevuelve SOLO un HTML completo con CSS y JavaScript internos. No uses markdown."
    text = route_text(prompt, task="artifact", system=system, max_tokens=4500, timeout_ms=75000)
    return clean_html(text)

def clean_html(text: str):
    t = text.strip()
    m = re.search(r"```(?:html)?\s*([\s\S]*?)```", t, re.I)
    if m:
        t = m.group(1).strip()
    if "<html" not in t.lower():
        t = "<!doctype html><html><head><meta charset='utf-8'><style>body{font-family:Segoe UI,Arial;background:#07111f;color:#e5f1ff;padding:32px}</style></head><body>" + t + "</body></html>"
    return t

ARKEA_AGENT_SYSTEM = """Eres ARKEA AI, un agente inteligente profesional, rápido y multimodal. Responde siempre en español claro, directo, breve y útil. No uses emojis en respuestas ni archivos. No empieces con muletillas como “wao”, “claro” o “perfecto”.

Sigue al pie de la letra la indicación del usuario. Si el usuario pide crear algo, entrega una acción concreta: archivo, vista previa, código funcional o documento generado.

Para páginas web, landing pages, juegos, sistemas, dashboards, formularios o apps, genera HTML completo en un solo archivo con CSS y JavaScript internos, diseño moderno, responsive y profesional.

Para Excel, genera libros reales con hojas separadas, encabezados, filas, colores, bordes, filtros y columnas ajustadas. No simules varias hojas dentro de una sola tabla.

Para Word o documentos largos, genera estructura formal, títulos, subtítulos, párrafos bien redactados, ortografía cuidada y presentación profesional. Si piden APA 7, aplica citas y referencias cuando existan fuentes.

Cuando el usuario suba archivos, usa su contenido como contexto. Si comparte pantalla o cámara, analiza la imagen recibida; no inventes lo que no ves.

Trabaja con continuidad: si el usuario pide corregir o modificar algo, modifica el artefacto actual cuando sea posible.

Prioridad: resultados reales, vista previa, código, descarga y posibilidad de modificar en tiempo real."""
