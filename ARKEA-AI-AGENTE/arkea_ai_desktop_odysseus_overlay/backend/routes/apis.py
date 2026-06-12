import json
from fastapi import APIRouter
from pydantic import BaseModel
from backend.arkea_core.db import rows, execute, one

router = APIRouter(prefix="/api/arkea/apis", tags=["apis"])

class ApiConnectionIn(BaseModel):
    api_type: str
    provider: str
    display_name: str = "default"
    base_url: str = ""
    api_key: str = ""
    model_id: str = ""
    extra: dict = {}
    enabled: bool = True


import requests
from fastapi import HTTPException

def _headers(api_key: str = "", extra: dict | None = None):
    h = {"Content-Type": "application/json"}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
        h["X-API-Key"] = api_key
    if extra:
        for k, v in extra.get("headers", {}).items():
            h[str(k)] = str(v)
    return h

def _friendly_api_error(text: str):
    t = (text or "")[:800]
    if "User not found" in t or '"code":401' in t:
        return "API key inválida o cuenta OpenRouter no encontrada. Genera una key nueva sk-or-v1... y vuelve a guardar la plantilla."
    if "unavailable for free" in t or "not a valid model ID" in t or '"code":404' in t or '"code":400' in t:
        return "Modelo OpenRouter no disponible o slug inválido. Usa las plantillas nuevas: Nex gratis, Qwen Coder free, DeepSeek V4 Flash o StepFun Flash. Detalle: " + t
    return t

def _json_load(v):
    try:
        return json.loads(v or "{}")
    except Exception:
        return {}

@router.post("/{api_id}/test")
def test_api(api_id: int):
    api = one("SELECT * FROM api_connections WHERE id=?", (api_id,))
    if not api:
        raise HTTPException(404, "API no encontrada")
    api_type = (api.get("api_type") or "").lower()
    provider = (api.get("provider") or "").lower()
    base_url = api.get("base_url") or ""
    api_key = api.get("api_key") or ""
    model_id = api.get("model_id") or ""
    extra = _json_load(api.get("extra_json"))

    if not base_url:
        return {"ok": False, "message": "Falta Base URL / endpoint."}
    if ("openrouter" in provider or "openrouter.ai" in base_url) and (not api_key or len(api_key.strip()) < 20):
        return {"ok": False, "message": "Falta una OPENROUTER_API_KEY válida. Pega una key sk-or-v1... en Recomendaciones y aplica la plantilla."}
    if model_id in ("google/gemini-2.5-flash:free", "xiaomi/mimo-flash:free", "openai/gpt-4o-mini"):
        return {"ok": False, "message": "Modelo desactualizado/no válido en OpenRouter. Elimínalo o pulsa 'Limpiar APIs rotas' y usa Nex/Qwen/DeepSeek/StepFun recomendados."}

    try:
        if provider in ("ollama_local", "ollama_vision") or "127.0.0.1:11434" in base_url or "localhost:11434" in base_url:
            payload = {"model": model_id or "gemma3:1b", "stream": False, "messages": [{"role":"user","content":"Responde solo: OK"}]}
            r = requests.post(base_url, json=payload, timeout=45)
            return {"ok": r.ok, "status": r.status_code, "provider": provider, "message": "Ollama respondió." if r.ok else _friendly_api_error(r.text)}

        if api_type in ("chat", "vision", "translation", "code", "artifact", "document", "file", "web_search"):
            payload = {
                "model": model_id,
                "messages": [{"role":"user", "content":"Responde solo: OK"}],
                "max_tokens": 16
            }
            if api_type == "web_search" or extra.get("web_search"):
                payload["web_search_options"] = {"search_context_size": "low"}
            r = requests.post(base_url, headers=_headers(api_key, extra), json=payload, timeout=45)
            return {"ok": r.ok, "status": r.status_code, "provider": provider, "message": "API chat/visión respondió." if r.ok else _friendly_api_error(r.text)}

        if api_type in ("image", "image_generation"):
            # OpenRouter no expone una API universal /images como OpenAI, pero ARKEA puede usarlo
            # como generador SVG/PNG por chat si el provider indica openrouter_svg_image.
            if "openrouter" in provider or "openrouter.ai" in base_url:
                payload = {"model": model_id or "openrouter/auto", "messages": [{"role":"user", "content":"Responde solo OK"}], "max_tokens": 8}
                r = requests.post(base_url, headers=_headers(api_key, extra), json=payload, timeout=45)
                return {"ok": r.ok, "status": r.status_code, "provider": provider, "message": "OpenRouter listo para imagen SVG/PNG asistida por modelo." if r.ok else _friendly_api_error(r.text)}
            if "stability" in provider or "replicate" in provider or "fal" in provider:
                return {"ok": True, "status": "saved", "provider": provider, "message": "API de imagen guardada. Se probará al generar imagen para evitar consumo innecesario."}
            payload = {"model": model_id, "prompt": "simple blue glass icon", "size": "512x512", "n": 1}
            r = requests.post(base_url, headers=_headers(api_key, extra), json=payload, timeout=90)
            return {"ok": r.ok, "status": r.status_code, "provider": provider, "message": "API de imagen respondió." if r.ok else _friendly_api_error(r.text)}

        if api_type == "voice_tts":
            if "elevenlabs" in provider or "{voice_id}" in base_url:
                voice_id = extra.get("voice_id") or model_id or ""
                url = base_url.replace("{voice_id}", voice_id)
                if not voice_id:
                    return {"ok": False, "message": "Falta voice_id en Model ID o Extra JSON."}
                payload = {"text":"OK", "model_id": extra.get("model_id") or "eleven_multilingual_v2"}
                r = requests.post(url, headers={"xi-api-key": api_key, "Content-Type":"application/json"}, json=payload, timeout=45)
                return {"ok": r.ok, "status": r.status_code, "provider": provider, "message": "TTS respondió." if r.ok else _friendly_api_error(r.text)}
            payload = {"model": model_id, "input": "OK", "voice": extra.get("voice","alloy")}
            r = requests.post(base_url, headers=_headers(api_key, extra), json=payload, timeout=45)
            return {"ok": r.ok, "status": r.status_code, "provider": provider, "message": "TTS respondió." if r.ok else _friendly_api_error(r.text)}

        if api_type == "voice_stt":
            return {"ok": True, "status": "saved", "provider": provider, "message": "STT guardado. La prueba real se hace al usar el botón Hablar con audio WAV."}

        if api_type in ("video", "automation", "embedding", "rerank", "custom"):
            # Conexión genérica: intenta OPTIONS/GET ligero.
            try:
                r = requests.options(base_url, headers=_headers(api_key, extra), timeout=20)
            except Exception:
                r = requests.get(base_url, headers=_headers(api_key, extra), timeout=20)
            return {"ok": r.status_code < 500, "status": r.status_code, "provider": provider, "message": "Endpoint alcanzable." if r.status_code < 500 else _friendly_api_error(r.text)}

        return {"ok": True, "status": "saved", "message": "API guardada. Tipo no reconocido para prueba automática."}
    except Exception as e:
        return {"ok": False, "provider": provider, "message": str(e)[:800]}

@router.get("")
def list_apis(api_type: str | None = None):
    if api_type:
        return {"apis": rows("SELECT id,api_type,provider,display_name,base_url,model_id,extra_json,enabled,created_at,updated_at FROM api_connections WHERE api_type=? ORDER BY provider, display_name", (api_type,))}
    return {"apis": rows("SELECT id,api_type,provider,display_name,base_url,model_id,extra_json,enabled,created_at,updated_at FROM api_connections ORDER BY api_type, provider, display_name")}

@router.post("/save")
def save_api(body: ApiConnectionIn):
    existing = one("SELECT id FROM api_connections WHERE api_type=? AND provider=? AND display_name=?", (body.api_type, body.provider, body.display_name))
    extra = json.dumps(body.extra or {}, ensure_ascii=False)
    if existing:
        execute("UPDATE api_connections SET base_url=?, api_key=?, model_id=?, extra_json=?, enabled=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (body.base_url, body.api_key, body.model_id, extra, int(body.enabled), existing['id']))
        return {"ok": True, "id": existing['id'], "updated": True}
    aid = execute("INSERT INTO api_connections(api_type,provider,display_name,base_url,api_key,model_id,extra_json,enabled) VALUES(?,?,?,?,?,?,?,?)", (body.api_type, body.provider, body.display_name, body.base_url, body.api_key, body.model_id, extra, int(body.enabled)))
    return {"ok": True, "id": aid, "created": True}

@router.post("/{api_id}/toggle")
def toggle(api_id: int):
    r = one("SELECT enabled FROM api_connections WHERE id=?", (api_id,))
    if not r:
        return {"ok": False, "error": "API no encontrada"}
    execute("UPDATE api_connections SET enabled=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (0 if r['enabled'] else 1, api_id))
    return {"ok": True}

@router.delete("/{api_id}")
def delete(api_id: int):
    execute("DELETE FROM api_connections WHERE id=?", (api_id,))
    return {"ok": True}


@router.post("/cleanup-broken")
def cleanup_broken():
    bad_patterns = ["google/gemini-2.5-flash:free", "xiaomi/mimo-flash:free", "openai/gpt-4o-mini"]
    disabled = 0
    for pat in bad_patterns:
        execute("UPDATE api_connections SET enabled=0, updated_at=CURRENT_TIMESTAMP WHERE model_id=?", (pat,))
        disabled += 1
    # También desactiva entradas OpenRouter vacías/de prueba sin clave para que no rompan el router.
    execute("UPDATE api_connections SET enabled=0, updated_at=CURRENT_TIMESTAMP WHERE (base_url LIKE '%openrouter.ai%' OR provider LIKE '%openrouter%') AND (api_key IS NULL OR api_key='' OR length(api_key)<20)")
    return {"ok": True, "message": "APIs rotas/desactualizadas desactivadas. Aplica una plantilla recomendada con tu API key actual."}

@router.get("/templates")
def templates():
    openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
    return {
        "types": ["chat","vision","code","artifact","document","file","web_search","image","image_generation","video","voice_tts","voice_stt","translation","embedding","rerank","automation","custom"],
        "recommended_presets": [
            {
                "id":"arkea_openrouter_free",
                "name":"ARKEA gratis estable / OpenRouter",
                "description":"No usa slugs rotos. Solo modelos que aparecen actualmente como gratis o de prueba en OpenRouter.",
                "provider":"openrouter",
                "base_url":openrouter_url,
                "needs_key":True,
                "items":[
                    {"api_type":"chat","provider":"openrouter_free_router","display_name":"ARKEA chat gratis router","model_id":"openrouter/free","extra":{"max_tokens":2200}},
                    {"api_type":"chat","provider":"openrouter_nemotron_free","display_name":"ARKEA chat gratis estable","model_id":"nvidia/nemotron-3-ultra-550b-a55b:free","extra":{"max_tokens":2200}},
                    {"api_type":"vision","provider":"openrouter_nex_vision_free","display_name":"ARKEA visión gratis estable","model_id":"nex-agi/nex-n2-pro:free","extra":{"max_tokens":900}},
                    {"api_type":"code","provider":"openrouter_qwen_code_free","display_name":"ARKEA código gratis","model_id":"qwen/qwen3-coder:free","extra":{"max_tokens":4500}},
                    {"api_type":"artifact","provider":"openrouter_qwen_artifact_free","display_name":"ARKEA artefactos/código gratis","model_id":"qwen/qwen3-coder:free","extra":{"max_tokens":4500}},
                    {"api_type":"image_generation","provider":"openrouter_svg_image_free","display_name":"ARKEA imagen PNG/SVG con OpenRouter","model_id":"qwen/qwen3-coder:free","extra":{"mode":"svg_to_png","max_tokens":2200}},
                    {"api_type":"file","provider":"openrouter_nex_file_free","display_name":"ARKEA archivos multimodal gratis","model_id":"nex-agi/nex-n2-pro:free","extra":{"max_tokens":2200}},
                    {"api_type":"web_search","provider":"openrouter_web_auto","display_name":"ARKEA internet auto","model_id":"openrouter/auto","extra":{"max_tokens":2200,"web_search":True}}
                ]
            },
            {
                "id":"arkea_openrouter_cheap",
                "name":"ARKEA barato recomendado / DeepSeek + StepFun + Qwen",
                "description":"Perfil económico para crear HTML, Word, Excel, PPT, analizar pantalla/cámara y escribir código.",
                "provider":"openrouter",
                "base_url":openrouter_url,
                "needs_key":True,
                "items":[
                    {"api_type":"chat","provider":"openrouter_deepseek_v4_flash","display_name":"ARKEA chat barato","model_id":"deepseek/deepseek-v4-flash","extra":{"max_tokens":2200}},
                    {"api_type":"artifact","provider":"openrouter_deepseek_artifacts","display_name":"ARKEA artefactos HTML/Word/Excel/PPT","model_id":"deepseek/deepseek-v4-flash","extra":{"max_tokens":4500,"stream_timeout_ms":75000}},
                    {"api_type":"document","provider":"openrouter_deepseek_docs","display_name":"ARKEA documentos largos","model_id":"deepseek/deepseek-v4-flash","extra":{"max_tokens":6500}},
                    {"api_type":"code","provider":"openrouter_qwen_code_flash","display_name":"ARKEA código barato rápido","model_id":"qwen/qwen3-coder-flash","extra":{"max_tokens":6500}},
                    {"api_type":"image_generation","provider":"openrouter_svg_image_cheap","display_name":"ARKEA imagen PNG/SVG barata","model_id":"qwen/qwen3-coder-flash","extra":{"mode":"svg_to_png","max_tokens":2800}},
                    {"api_type":"vision","provider":"openrouter_vision_step_flash","display_name":"ARKEA visión barata pantalla/cámara","model_id":"stepfun/step-3.7-flash","extra":{"max_tokens":1000}},
                    {"api_type":"vision","provider":"openrouter_vision_xiaomi_v25","display_name":"ARKEA visión Xiaomi V2.5 barata","model_id":"xiaomi/mimo-v2.5","extra":{"max_tokens":1000}},
                    {"api_type":"vision","provider":"openrouter_vision_qwen_plus","display_name":"ARKEA visión alternativa Qwen","model_id":"qwen/qwen3.7-plus","extra":{"max_tokens":1000}},
                    {"api_type":"file","provider":"openrouter_file_multimodal_cheap","display_name":"ARKEA archivos multimodal barato","model_id":"minimax/minimax-m3","extra":{"max_tokens":3000}},
                    {"api_type":"web_search","provider":"openrouter_web_auto","display_name":"ARKEA internet auto","model_id":"openrouter/auto","extra":{"max_tokens":3000,"web_search":True}}
                ]
            },
            {
                "id":"arkea_openrouter_env_compat",
                "name":"Compatible con tu plantilla ENV anterior",
                "description":"Replica tu flujo OPENROUTER_MODEL / STREAM_MODEL / FILE_MODEL pero con slugs válidos y baratos.",
                "provider":"openrouter",
                "base_url":openrouter_url,
                "needs_key":True,
                "items":[
                    {"api_type":"chat","provider":"openrouter_env_chat","display_name":"OPENROUTER_MODEL","model_id":"deepseek/deepseek-v4-flash","extra":{"max_tokens":2200}},
                    {"api_type":"artifact","provider":"openrouter_env_artifact","display_name":"STREAM_MODEL","model_id":"deepseek/deepseek-v4-flash","extra":{"max_tokens":4500,"stream_timeout_ms":75000}},
                    {"api_type":"code","provider":"openrouter_env_code","display_name":"CODE_MODEL","model_id":"qwen/qwen3-coder-flash","extra":{"max_tokens":6500}},
                    {"api_type":"image_generation","provider":"openrouter_env_image","display_name":"IMAGE_MODEL","model_id":"qwen/qwen3-coder-flash","extra":{"mode":"svg_to_png","max_tokens":2800}},
                    {"api_type":"vision","provider":"openrouter_env_vision","display_name":"VISION_MODEL","model_id":"stepfun/step-3.7-flash","extra":{"max_tokens":1000}},
                    {"api_type":"file","provider":"openrouter_env_file","display_name":"OPENROUTER_FILE_MODEL","model_id":"minimax/minimax-m3","extra":{"max_tokens":3000}},
                    {"api_type":"web_search","provider":"openrouter_env_web","display_name":"ENABLE_WEB_SEARCH","model_id":"openrouter/auto","extra":{"max_tokens":3000,"web_search":True,"site_url":"https://abridorrompe.rf.gd","allowed_origin":"*"}}
                ]
            }
        ],
        "providers": {
            "chat":[
                {"provider":"openai_chat","base_url":"https://api.openai.com/v1/chat/completions","model":"gpt-4o-mini"},
                {"provider":"openrouter_deepseek_v4_flash","base_url":openrouter_url,"model":"deepseek/deepseek-v4-flash"},
                {"provider":"openrouter_nemotron_free","base_url":openrouter_url,"model":"nvidia/nemotron-3-ultra-550b-a55b:free"},
                {"provider":"openrouter_auto","base_url":openrouter_url,"model":"openrouter/auto"},
                {"provider":"ollama_local","base_url":"http://127.0.0.1:11434/api/chat","model":"gemma3:270m"},
                {"provider":"custom","base_url":"","model":""}
            ],
            "vision":[
                {"provider":"openrouter_nex_vision_free","base_url":openrouter_url,"model":"nex-agi/nex-n2-pro:free"},
                {"provider":"openrouter_vision_step_flash","base_url":openrouter_url,"model":"stepfun/step-3.7-flash"},
                {"provider":"openrouter_vision_xiaomi_v25","base_url":openrouter_url,"model":"xiaomi/mimo-v2.5"},
                {"provider":"openrouter_vision_qwen_plus","base_url":openrouter_url,"model":"qwen/qwen3.7-plus"},
                {"provider":"openrouter_vision_minimax","base_url":openrouter_url,"model":"minimax/minimax-m3"},
                {"provider":"openai_vision","base_url":"https://api.openai.com/v1/chat/completions","model":"gpt-4o-mini"},
                {"provider":"ollama_vision","base_url":"http://127.0.0.1:11434/api/chat","model":"gemma3:4b"},
                {"provider":"custom","base_url":"","model":""}
            ],
            "code":[
                {"provider":"openrouter_qwen_code_free","base_url":openrouter_url,"model":"qwen/qwen3-coder:free"},
                {"provider":"openrouter_qwen_code_flash","base_url":openrouter_url,"model":"qwen/qwen3-coder-flash"},
                {"provider":"openrouter_deepseek_code","base_url":openrouter_url,"model":"deepseek/deepseek-v4-flash"},
                {"provider":"ollama_code","base_url":"http://127.0.0.1:11434/api/chat","model":"qwen2.5-coder:0.5b"},
                {"provider":"custom","base_url":"","model":""}
            ],
            "artifact":[
                {"provider":"openrouter_qwen_artifact_free","base_url":openrouter_url,"model":"qwen/qwen3-coder:free"},
                {"provider":"openrouter_artifact_deepseek","base_url":openrouter_url,"model":"deepseek/deepseek-v4-flash"},
                {"provider":"openrouter_artifact_qwen_flash","base_url":openrouter_url,"model":"qwen/qwen3-coder-flash"},
                {"provider":"openrouter_auto","base_url":openrouter_url,"model":"openrouter/auto"},
                {"provider":"custom","base_url":"","model":""}
            ],
            "document":[
                {"provider":"openrouter_deepseek_docs","base_url":openrouter_url,"model":"deepseek/deepseek-v4-flash"},
                {"provider":"openrouter_file_multimodal_cheap","base_url":openrouter_url,"model":"minimax/minimax-m3"},
                {"provider":"openrouter_auto","base_url":openrouter_url,"model":"openrouter/auto"},
                {"provider":"custom","base_url":"","model":""}
            ],
            "file":[
                {"provider":"openrouter_file_multimodal_cheap","base_url":openrouter_url,"model":"minimax/minimax-m3"},
                {"provider":"openrouter_nex_file_free","base_url":openrouter_url,"model":"nex-agi/nex-n2-pro:free"},
                {"provider":"openrouter_auto","base_url":openrouter_url,"model":"openrouter/auto"},
                {"provider":"custom","base_url":"","model":""}
            ],
            "web_search":[
                {"provider":"openrouter_web_auto","base_url":openrouter_url,"model":"openrouter/auto"},
                {"provider":"openrouter_web_deepseek","base_url":openrouter_url,"model":"deepseek/deepseek-v4-flash"},
                {"provider":"perplexity_sonar_pro","base_url":openrouter_url,"model":"perplexity/sonar-pro-search"},
                {"provider":"custom","base_url":"","model":""}
            ],
            "image":[
                {"provider":"openai_images","base_url":"https://api.openai.com/v1/images/generations","model":"gpt-image-1"},
                {"provider":"stability_core","base_url":"https://api.stability.ai/v2beta/stable-image/generate/core","model":"stable-image-core"},
                {"provider":"fal_flux_schnell","base_url":"https://fal.run/fal-ai/flux/schnell","model":"flux-schnell"},
                {"provider":"replicate_flux_schnell","base_url":"https://api.replicate.com/v1/predictions","model":"black-forest-labs/flux-schnell"},
                {"provider":"comfyui_local","base_url":"http://127.0.0.1:8188","model":"workflow"},
                {"provider":"automatic1111_local","base_url":"http://127.0.0.1:7860/sdapi/v1/txt2img","model":"local"},
                {"provider":"custom","base_url":"","model":""}
            ],
            "image_generation":[
                {"provider":"openrouter_svg_image_cheap","base_url":openrouter_url,"model":"qwen/qwen3-coder-flash"},
                {"provider":"openai_images","base_url":"https://api.openai.com/v1/images/generations","model":"gpt-image-1"},
                {"provider":"fal_flux_schnell","base_url":"https://fal.run/fal-ai/flux/schnell","model":"flux-schnell"},
                {"provider":"comfyui_local","base_url":"http://127.0.0.1:8188","model":"workflow"},
                {"provider":"custom","base_url":"","model":""}
            ],
            "video":[{"provider":"openrouter_video_auto","base_url":openrouter_url,"model":"openrouter/auto"},{"provider":"custom","base_url":"","model":""}],
            "voice_tts":[{"provider":"elevenlabs","base_url":"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}","model":"eleven_multilingual_v2"},{"provider":"openai_tts","base_url":"https://api.openai.com/v1/audio/speech","model":"gpt-4o-mini-tts"},{"provider":"custom","base_url":"","model":""}],
            "voice_stt":[{"provider":"openai_whisper","base_url":"https://api.openai.com/v1/audio/transcriptions","model":"whisper-1"},{"provider":"deepgram","base_url":"https://api.deepgram.com/v1/listen","model":"nova-3"},{"provider":"local_whisper","base_url":"http://127.0.0.1:9000/transcribe","model":"faster-whisper"},{"provider":"custom","base_url":"","model":""}],
            "embedding":[{"provider":"ollama_embeddings","base_url":"http://127.0.0.1:11434/api/embeddings","model":"nomic-embed-text"},{"provider":"custom","base_url":"","model":""}],
            "automation":[{"provider":"browser_local","base_url":"http://127.0.0.1:9222","model":"browser"},{"provider":"mcp_server","base_url":"stdio/http","model":"tool"},{"provider":"custom","base_url":"","model":""}],
            "translation":[{"provider":"custom","base_url":"","model":""}],
            "rerank":[{"provider":"custom","base_url":"","model":""}],
            "custom":[{"provider":"custom","base_url":"","model":""}]
        }
    }

