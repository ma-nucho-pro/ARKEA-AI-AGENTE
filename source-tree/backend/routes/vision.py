import json, requests, re
from fastapi import APIRouter
from pydantic import BaseModel, Field
from backend.arkea_core.db import rows, get_setting
from backend.arkea_core import ollama
from backend.arkea_core import omniroute
from backend.arkea_core.security import guarded_request
from backend.arkea_core.agent_runtime import enrich_system_prompt

router = APIRouter(prefix="/api/arkea/vision", tags=["vision"])

class VisionIn(BaseModel):
    image_data_url: str = Field(min_length=1, max_length=16_000_000)
    prompt: str = Field(default="Describe brevemente lo que ves. Responde en español.", max_length=4_000)
    source: str = Field(default="camera", max_length=30)

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
          OR (api_type='chat' AND (provider LIKE '%openai%' OR provider LIKE '%openrouter%' OR provider='omniroute' OR base_url LIKE '%openai%' OR base_url LIKE '%openrouter%' OR base_url LIKE '%127.0.0.1:20128%'))
        )
        ORDER BY CASE WHEN api_type='vision' THEN 0 ELSE 1 END, updated_at DESC, id DESC
    """)
    apis = [a for a in (apis or []) if not _bad_api(a)]
    mode = (get_setting("ai_engine_mode", "auto") or "auto").lower()
    if mode in {"auto", "free"} and not any((a.get("provider") or "").lower() == "omniroute" for a in apis):
        apis.insert(0, omniroute.connection_for("vision"))
    if mode == "free":
        return [a for a in apis if (a.get("provider") or "").lower() == "omniroute"]
    if mode == "direct":
        return [a for a in apis if _is_direct_vision_provider(a)]
    return sorted(apis, key=lambda a: 0 if (a.get("provider") or "").lower() == "omniroute" else 1)


def _is_direct_vision_provider(api: dict) -> bool:
    provider = (api.get("provider") or "").strip().lower()
    base_url = (api.get("base_url") or "").strip().lower()
    if provider == "omniroute" or provider.startswith("ollama") or provider.endswith("_local"):
        return False
    return not any(
        marker in base_url
        for marker in ("127.0.0.1", "localhost", "[::1]", "0.0.0.0")
    )

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
    if not api.get("base_url"):
        return None
    provider = (api.get("provider") or "").lower()
    if provider != "omniroute" and not api.get("api_key"):
        return None
    model = api.get("model_id") or ("openai/gpt-4o-mini" if "openrouter" in (api.get("provider") or "").lower() else "gpt-4o-mini")
    payload = {
        "model": model,
        "messages": [{
            "role": "system",
            "content": enrich_system_prompt(
                "Eres el módulo de visión de ARKEA AI. Describe solo lo que realmente ves.",
                "vision",
            )[:12_000],
        }, {
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
    r = guarded_request(
        "POST", api["base_url"], allow_local=provider == "omniroute",
        headers=_headers(api), json=payload, timeout=45
    )
    r.raise_for_status()
    data = r.json()
    text = _extract_text(data).strip()
    if not text:
        text = "La API respondió, pero no devolvió una descripción visible. Prueba otro modelo de visión."
    decision = r.headers.get("X-OmniRoute-Decision", "")
    if provider == "omniroute":
        omniroute.remember_decision(decision or f"vision model={model}")
    return {"ok": True, "say": text, "source": body.source, "provider": api.get("provider"), "model": model, "mode": "cloud", "decision": decision}

@router.post("/analyze")
def analyze(body: VisionIn):
    engine_mode = (get_setting("ai_engine_mode", "auto") or "auto").lower()
    # 1) Primero internet/API si está configurada. Esto permite “ver pantalla” aunque el modelo local sea débil.
    api_errors = []
    for api in ([] if engine_mode == "local" else _candidate_vision_apis()):
        try:
            out = _call_cloud_vision(api, body)
            if out:
                return out
        except Exception as e:
            # No mostrar errores largos de APIs incompletas en el chat.
            api_errors.append(f"{api.get('provider') or api.get('display_name')}: {str(e)[:120]}")

    # 2) Luego local Ollama con modelos de visión.
    if engine_mode == "free":
        return {
            "ok": False,
            "say": "El modo IA gratis está activo, pero OmniRoute no pudo analizar esta imagen. Elige un modelo o combo multimodal en IA universal.",
            "source": body.source,
            "status": "omniroute_vision_unavailable",
        }
    if engine_mode == "direct":
        return {
            "ok": False,
            "say": "El modo API directa está activo, pero ninguna API de visión configurada respondió. No se usó OmniRoute ni Ollama.",
            "source": body.source,
            "status": "direct_vision_unavailable",
        }

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
                r = guarded_request("POST", f"{ollama.base_url()}/api/chat", allow_local=True, json=payload, timeout=45)
                r.raise_for_status()
                text = r.json().get("message", {}).get("content", "").strip()
                return {"ok": True, "say": _clean_vision_text(text), "source": body.source, "provider": "ollama", "model": model, "mode": "local"}
    except Exception as e:
        api_errors.append("ollama: " + str(e)[:160])

    # 3) Mensaje claro, sin hacer creer que “vio” si no hay modelo real.
    msg = "Puedo mostrar pantalla/cámara, pero para describirla necesitas una API de visión válida o un modelo local de visión. Recomendado en APIS: nex-agi/nex-n2-pro:free, stepfun/step-3.7-flash o qwen/qwen3.7-plus."
    return {"ok": True, "say": msg, "source": body.source, "status": "needs_vision_api_or_model"}
