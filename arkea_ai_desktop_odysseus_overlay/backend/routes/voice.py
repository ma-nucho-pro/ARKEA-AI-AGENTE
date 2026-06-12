import os, requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from backend.arkea_core.db import get_setting

router = APIRouter(prefix="/api/arkea/voice", tags=["voice"])

class TTSIn(BaseModel):
    text: str
    voice_id: str | None = None

@router.post("/elevenlabs")
def elevenlabs_tts(body: TTSIn):
    api_key = get_setting("elevenlabs_api_key", "") or os.getenv("ELEVENLABS_API_KEY", "")
    voice_id = body.voice_id or get_setting("elevenlabs_voice_id", "") or os.getenv("ELEVENLABS_VOICE_ID", "")
    if not api_key or not voice_id:
        raise HTTPException(400, "Configura ElevenLabs API Key y Voice ID en Ajustes > APIs y voz")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": body.text,
        "model_id": get_setting("elevenlabs_model_id", "eleven_multilingual_v2") or "eleven_multilingual_v2",
        "voice_settings": {
            "stability": float(get_setting("elevenlabs_stability", "0.45") or 0.45),
            "similarity_boost": float(get_setting("elevenlabs_similarity", "0.8") or 0.8)
        }
    }
    r = requests.post(url, headers={"xi-api-key": api_key, "Content-Type":"application/json"}, json=payload, timeout=90)
    if not r.ok:
        raise HTTPException(r.status_code, r.text[:500])
    return Response(content=r.content, media_type="audio/mpeg")


@router.get("/elevenlabs/voices")
def elevenlabs_voices():
    api_key = get_setting("elevenlabs_api_key", "") or os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key:
        return {"voices": [], "error": "Configura ElevenLabs API Key"}
    r = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": api_key}, timeout=45)
    if not r.ok:
        return {"voices": [], "error": r.text[:300]}
    data = r.json()
    return {"voices": [{"name": v.get("name"), "voice_id": v.get("voice_id")} for v in data.get("voices", [])]}

@router.get("/mic/help")
def mic_help():
    return {
        "title": "Activar micrófono en Windows",
        "steps": [
            "Abre Configuración de Windows.",
            "Entra a Privacidad y seguridad > Micrófono.",
            "Activa Permitir acceso al micrófono.",
            "Activa Permitir que las aplicaciones de escritorio accedan al micrófono.",
            "Cierra y vuelve a abrir ARKEA AI Desktop.",
            "Si aparece error network, configura una API STT/Whisper en Ajustes > APIS > Voz a texto. Chromium puede depender de un servicio de red para SpeechRecognition."
        ]
    }


from fastapi import UploadFile, File, Form
from pathlib import Path
import tempfile, json
from backend.arkea_core.db import rows


_WHISPER_MODEL_CACHE = {}

def _enabled_stt_api():
    apis = rows("SELECT * FROM api_connections WHERE api_type='voice_stt' AND enabled=1 ORDER BY updated_at DESC, id DESC LIMIT 1")
    return apis[0] if apis else None

@router.post('/transcribe')
async def transcribe_audio(file: UploadFile = File(...), language: str = Form('es')):
    """Transcribe WAV audio. First tries configured STT API, then local faster-whisper."""
    content = await file.read()
    api = _enabled_stt_api()
    if api and api.get('api_key') and api.get('base_url'):
        try:
            provider = (api.get('provider') or '').lower()
            headers = {'Authorization': f"Bearer {api['api_key']}"}
            files = {'file': (file.filename or 'audio.wav', content, 'audio/wav')}
            data = {'model': api.get('model_id') or 'whisper-1', 'language': language or 'es'}
            r = requests.post(api['base_url'], headers=headers, files=files, data=data, timeout=180)
            r.raise_for_status()
            jd = r.json()
            text = jd.get('text') or jd.get('transcript') or jd.get('transcription') or ''
            if text:
                return {'ok': True, 'text': text, 'provider': api.get('provider')}
            return {'ok': False, 'error': 'La API STT respondió sin texto.', 'raw': jd}
        except Exception as e:
            last_error = 'API STT: ' + str(e)
    else:
        last_error = 'Sin API STT configurada.'

    # Local faster-whisper fallback. The model is downloaded once to the user cache.
    try:
        from faster_whisper import WhisperModel
        model_size = get_setting('local_whisper_model', 'tiny') or 'tiny'
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        # Modelo cacheado: evita recargar Whisper en cada dictado y acelera el flujo de voz.
        cache_key = f"{model_size}:cpu:int8"
        if cache_key not in _WHISPER_MODEL_CACHE:
            _WHISPER_MODEL_CACHE[cache_key] = _WHISPER_MODEL_CACHE.setdefault(model_size, WhisperModel(model_size, device='cpu', compute_type='int8'))
        model = _WHISPER_MODEL_CACHE[cache_key]
        segments, info = model.transcribe(tmp_path, language=language or 'es', vad_filter=False, beam_size=1)
        text = ' '.join(seg.text.strip() for seg in segments).strip()
        try: os.remove(tmp_path)
        except Exception: pass
        return {'ok': True, 'text': text, 'provider': 'local_faster_whisper', 'model': model_size}
    except Exception as e:
        return {'ok': False, 'text': '', 'error': last_error + ' | Whisper local: ' + str(e), 'help': 'Configura una API STT en Ajustes > APIS o instala/compila faster-whisper con modelo tiny.'}

@router.post('/install-whisper-default')
def install_whisper_default():
    from backend.arkea_core.db import upsert_setting
    upsert_setting('local_whisper_model', 'tiny')
    try:
        from faster_whisper import WhisperModel
        # Fuerza descarga/preparación inicial del modelo tiny en el cache del usuario y lo deja cacheado.
        _WHISPER_MODEL_CACHE['tiny:cpu:int8'] = WhisperModel('tiny', device='cpu', compute_type='int8')
        return {'ok': True, 'message': 'Whisper tiny quedó descargado/activado para dictado local. Ya puedes hablar y se transcribirá en el chat.'}
    except Exception as e:
        return {
            'ok': False,
            'message': 'No pude descargar/preparar Whisper tiny automáticamente. Revisa internet o configura una API voice_stt. Error: ' + str(e),
            'download_url': 'https://huggingface.co/Systran/faster-whisper-tiny'
        }


@router.post('/install-whisper')
def install_whisper_alias():
    return install_whisper_default()
