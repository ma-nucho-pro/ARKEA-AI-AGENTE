import json, requests, time, re
from backend.arkea_core.db import rows, get_setting
from backend.arkea_core.ollama import chat_local

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
    return [a for a in out if not _bad_api(a)]

def _score(api, task):
    provider = (api.get("provider") or "").lower()
    model = (api.get("model_id") or "").lower()
    score = 0
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

def route_text(message: str, task: str = "chat", system: str = "", max_tokens: int | None = None, timeout_ms: int | None = None):
    api = pick_api(task)
    if not api:
        return chat_local(message, system=system or "Eres ARKEA AI.")
    extra = _j(api.get("extra_json"))
    base_url = api.get("base_url") or OPENROUTER_URL
    model = api.get("model_id") or ("openrouter/auto" if task in ("web","file") else "deepseek/deepseek-v4-flash")
    mt = max_tokens or int(extra.get("max_tokens") or (4500 if task in ("artifact","code") else 2200))
    timeout = (timeout_ms or int(extra.get("stream_timeout_ms") or 75000)) / 1000
    payload = {
        "model": model,
        "messages": [
            {"role":"system","content": system or ARKEA_AGENT_SYSTEM},
            {"role":"user","content": message}
        ],
        "max_tokens": mt,
        "temperature": 0.25
    }
    if task == "web" or extra.get("web_search"):
        payload["web_search_options"] = {"search_context_size":"medium"}
    try:
        r = requests.post(base_url, headers=_headers(api), json=payload, timeout=timeout)
        r.raise_for_status()
        txt = _extract_content(r.json()).strip()
        return txt or "Listo."
    except Exception as e:
        # fallback local sin colgar la app
        fallback = chat_local(message, system=system or "Eres ARKEA AI.")
        if fallback:
            return fallback
        return f"No pude usar la API seleccionada ({model}). Revisa API key/modelo en Ajustes > APIS."

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
