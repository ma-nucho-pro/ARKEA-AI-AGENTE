import json, requests, re
from fastapi import APIRouter
from pydantic import BaseModel
from backend.arkea_core.db import rows
from backend.arkea_core import ollama

router = APIRouter(prefix="/api/arkea/vision", tags=["vision"])

class VisionIn(BaseModel):
    image_data_url: str
    prompt: str = "Describe brevemente lo que ves. Responde en español."
    source: str = "camera"

def _strip_data_url(data_url: str):
    return data_url.split(",", 1)[1] if "," in data_url else data_url

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

def _candidate_vision_apis():
    # Prioridad: APIs tipo vision. Si no hay, usa chat API compatible OpenAI/OpenRouter como respaldo con imagen.
    apis = rows("""
        SELECT * FROM api_connections
        WHERE enabled=1 AND (
          api_type='vision'
          OR (api_type='chat' AND (provider LIKE '%openai%' OR provider LIKE '%openrouter%' OR base_url LIKE '%openai%' OR base_url LIKE '%openrouter%'))
        )
        ORDER BY CASE WHEN api_type='vision' THEN 0 ELSE 1 END, updated_at DESC, id DESC
    """)
    return [a for a in (apis or []) if not _bad_api(a)]

def _headers(api):
    key = api.get("api_key") or ""
    provider = (api.get("provider") or "").lower()
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if "openrouter" in provider or "openrouter" in (api.get("base_url") or ""):
        headers["HTTP-Referer"] = "http://127.0.0.1"
        headers["X-Title"] = "ARKEA AI"
    return headers

def _clean_vision_text(t: str):
    t = str(t or "").strip().replace("```", "")
    if t.startswith("{"):
        try:
            data = json.loads(t)
            t = _extract_text(data) or ""
        except Exception:
            t = ""
    t = re.sub(r"\*\*|__|#+", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    for pat in [r"^El usuario quiere[^.]*\.\s*", r"^Voy a [^.]*\.\s*", r"^Necesito [^.]*\.\s*", r"^Analizar la imagen[:：]?\s*", r"^1\.\s*Analizar la imagen[:：]?\s*"]:
        t = re.sub(pat, "", t, flags=re.I)
    labels = re.findall(r"(?:Persona|Fondo|Objeto|Texto|Pantalla|Cámara|Camara|Ventana|Documento|Rostro|Color|Elemento)[:：]\s*([^.;\n]+)", t, flags=re.I)
    if labels:
        t = "Veo " + "; ".join(labels[:5]) + "."
    if not t:
        return "No recibí una descripción clara de la imagen."
    if len(t) > 360:
        t = t[:360].rsplit(" ",1)[0] + "…"
    return t

def _extract_text(data):
    if isinstance(data, dict):
        try:
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content")
            if isinstance(content, str) and content.strip():
                return _clean_vision_text(content)
            reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
            if reasoning:
                return _clean_vision_text(reasoning)
        except Exception:
            pass
        for k in ("text", "output_text", "content", "message", "reasoning"):
            v = data.get(k)
            if isinstance(v, str) and v.strip():
                return _clean_vision_text(v)
        for v in data.values():
            if isinstance(v, (dict, list)):
                found = _extract_text(v)
                if found:
                    return found
    if isinstance(data, list):
        for v in data[:4]:
            found = _extract_text(v)
            if found:
                return found
    return ""

def _call_cloud_vision(api, body: VisionIn):
    if not api.get("base_url") or not api.get("api_key"):
        return None
    model = api.get("model_id") or ("openai/gpt-4o-mini" if "openrouter" in (api.get("provider") or "").lower() else "gpt-4o-mini")
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": body.prompt or "Describe lo que ves en la imagen en español."},
                {"type": "image_url", "image_url": {"url": body.image_data_url}}
            ]
        }],
        "max_tokens": 160,
        "temperature": 0.2,
        "include_reasoning": False
    }
    r = requests.post(api["base_url"], headers=_headers(api), json=payload, timeout=45)
    r.raise_for_status()
    data = r.json()
    text = _extract_text(data).strip()
    if not text:
        text = "La API respondió, pero no devolvió una descripción visible. Prueba otro modelo de visión."
    return {"ok": True, "say": text, "source": body.source, "provider": api.get("provider"), "model": model, "mode": "cloud"}

@router.post("/analyze")
def analyze(body: VisionIn):
    # 1) Primero internet/API si está configurada. Esto permite “ver pantalla” aunque el modelo local sea débil.
    api_errors = []
    for api in _candidate_vision_apis():
        try:
            out = _call_cloud_vision(api, body)
            if out:
                return out
        except Exception as e:
            # No mostrar errores largos de APIs incompletas en el chat.
            api_errors.append(f"{api.get('provider') or api.get('display_name')}: {str(e)[:120]}")

    # 2) Luego local Ollama con modelos de visión.
    try:
        st = ollama.status(fast=True)
        if st.get("installed") and st.get("running"):
            installed = [m.get("name") or m.get("model") or "" for m in st.get("models", [])]
            vision_candidates = [m for m in installed if any(x in m.lower() for x in ["gemma3:4b", "gemma4", "llava", "moondream"])]
            if vision_candidates:
                model = vision_candidates[0]
                payload = {
                    "model": model,
                    "stream": False,
                    "messages": [{
                        "role": "user",
                        "content": body.prompt or "Identifica objetos principales visibles. Responde en español.",
                        "images": [_strip_data_url(body.image_data_url)]
                    }],
                    "options": {"num_predict": 110, "num_ctx": 1024, "temperature": 0.2}
                }
                r = requests.post(f"{ollama.base_url()}/api/chat", json=payload, timeout=45)
                r.raise_for_status()
                text = r.json().get("message", {}).get("content", "").strip()
                return {"ok": True, "say": _clean_vision_text(text), "source": body.source, "provider": "ollama", "model": model, "mode": "local"}
    except Exception as e:
        api_errors.append("ollama: " + str(e)[:160])

    # 3) Mensaje claro, sin hacer creer que “vio” si no hay modelo real.
    msg = "Puedo mostrar pantalla/cámara, pero para describirla necesitas una API de visión válida o un modelo local de visión. Recomendado en APIS: nex-agi/nex-n2-pro:free, stepfun/step-3.7-flash o qwen/qwen3.7-plus."
    return {"ok": True, "say": msg, "source": body.source, "status": "needs_vision_api_or_model"}
