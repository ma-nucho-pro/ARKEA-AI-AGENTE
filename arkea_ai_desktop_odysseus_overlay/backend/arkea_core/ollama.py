import os, shutil, subprocess, requests, sys, time, tempfile
from pathlib import Path
from backend.arkea_core.hardware import get_hardware_profile, tier_from_ram
try:
    from backend.arkea_core.db import get_setting
except Exception:
    get_setting = None

DEFAULT_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

MODEL_CATALOG = [
    {'id': 'gemma3:270m', 'name': 'Gemma 3 270M', 'category':'chat', 'task': 'chat/traducción muy ligera', 'ram_min_gb': 4, 'disk_gb': 0.4, 'local': True, 'vision': False, 'note': 'Ultra ligero para PCs muy básicas.'},
    {'id': 'gemma3:1b', 'name': 'Gemma 3 1B', 'category':'chat', 'task': 'chat/traducción', 'ram_min_gb': 6, 'disk_gb': 1.0, 'local': True, 'vision': False, 'note': 'Recomendado por defecto para bajos recursos.'},
    {'id': 'llama3.2:1b', 'name': 'Llama 3.2 1B', 'category':'chat', 'task': 'chat rápido', 'ram_min_gb': 6, 'disk_gb': 1.5, 'local': True, 'vision': False, 'note': 'Rápido y sencillo.'},
    {'id': 'llama3.2:3b', 'name': 'Llama 3.2 3B', 'category':'chat', 'task': 'chat mejorado', 'ram_min_gb': 10, 'disk_gb': 2.2, 'local': True, 'vision': False, 'note': 'Mejor calidad manteniendo recursos moderados.'},
    {'id': 'qwen3:0.6b', 'name': 'Qwen 3 0.6B', 'category':'chat', 'task': 'chat ligero', 'ram_min_gb': 4, 'disk_gb': 0.7, 'local': True, 'vision': False, 'note': 'Modelo moderno muy ligero si está disponible en Ollama.'},
    {'id': 'qwen3:1.7b', 'name': 'Qwen 3 1.7B', 'category':'chat', 'task': 'chat razonamiento ligero', 'ram_min_gb': 8, 'disk_gb': 1.6, 'local': True, 'vision': False, 'note': 'Buen equilibrio para tareas generales.'},
    {'id': 'qwen2.5-coder:0.5b', 'name': 'Qwen2.5 Coder 0.5B', 'category':'code', 'task': 'código ultra ligero', 'ram_min_gb': 4, 'disk_gb': 0.5, 'local': True, 'vision': False, 'note': 'Para crear/editar código en PCs débiles.'},
    {'id': 'qwen2.5-coder:1.5b', 'name': 'Qwen2.5 Coder 1.5B', 'category':'code', 'task': 'código', 'ram_min_gb': 8, 'disk_gb': 1.2, 'local': True, 'vision': False, 'note': 'Mejor equilibrio para ARKEA tipo Codex.'},
    {'id': 'qwen2.5-coder:3b', 'name': 'Qwen2.5 Coder 3B', 'category':'code', 'task': 'código mejorado', 'ram_min_gb': 12, 'disk_gb': 2.5, 'local': True, 'vision': False, 'note': 'Más calidad si tienes al menos 12 GB RAM.'},
    {'id': 'deepseek-coder:1.3b', 'name': 'DeepSeek Coder 1.3B', 'category':'code', 'task': 'código ligero', 'ram_min_gb': 8, 'disk_gb': 1.5, 'local': True, 'vision': False, 'note': 'Alternativa local ligera para código.'},
    {'id': 'gemma3:4b', 'name': 'Gemma 3 4B Vision', 'category':'vision', 'task': 'visión + chat', 'ram_min_gb': 12, 'disk_gb': 3.5, 'local': True, 'vision': True, 'note': 'Modelo local recomendado para analizar imágenes/cámara.'},
    {'id': 'gemma4:e2b-it-q4_K_M', 'name': 'Gemma 4 E2B', 'category':'vision', 'task': 'chat/razonamiento/visión', 'ram_min_gb': 12, 'disk_gb': 4.0, 'local': True, 'vision': True, 'note': 'Multimodal si el tag existe. Analiza imágenes; no genera imágenes.'},
    {'id': 'llava:7b', 'name': 'LLaVA 7B', 'category':'vision', 'task': 'visión general', 'ram_min_gb': 16, 'disk_gb': 4.7, 'local': True, 'vision': True, 'note': 'Alternativa local para análisis visual.'},
    {'id': 'moondream:latest', 'name': 'Moondream', 'category':'vision', 'task': 'visión ligera', 'ram_min_gb': 8, 'disk_gb': 2.0, 'local': True, 'vision': True, 'note': 'Visión ligera si está disponible.'},
    {'id': 'bge-m3', 'name': 'BGE-M3', 'category':'embedding', 'task': 'embeddings/búsqueda semántica', 'ram_min_gb': 8, 'disk_gb': 1.2, 'local': True, 'vision': False, 'note': 'Útil para memoria y recuperación semántica local.'},
    {'id': 'nomic-embed-text', 'name': 'Nomic Embed Text', 'category':'embedding', 'task': 'embeddings ligeros', 'ram_min_gb': 6, 'disk_gb': 0.8, 'local': True, 'vision': False, 'note': 'Embeddings locales para memoria.'},
    {'id': 'whisper:local', 'name': 'Whisper local', 'category':'voice', 'task': 'voz a texto', 'ram_min_gb': 4, 'disk_gb': 1.0, 'local': False, 'vision': False, 'note': 'ARKEA usa faster-whisper local desde Ajustes > APIS/Whisper.'},
    {'id': 'gpt-image-1:api', 'name': 'GPT Image 1 (API)', 'category':'image', 'task': 'creación de imágenes', 'ram_min_gb': 4, 'disk_gb': 0, 'local': False, 'vision': False, 'note': 'Se usa desde APIS > image.'},
    {'id': 'flux-schnell:api', 'name': 'FLUX Schnell (API/Replicate/FAL)', 'category':'image', 'task': 'creación de imágenes', 'ram_min_gb': 4, 'disk_gb': 0, 'local': False, 'vision': False, 'note': 'Rápido para imagen por API.'},
    {'id': 'stable-diffusion:local', 'name': 'Stable Diffusion Local', 'category':'image', 'task': 'creación/edición local de imágenes', 'ram_min_gb': 16, 'disk_gb': 8, 'local': False, 'vision': False, 'note': 'Conectar por ComfyUI o Automatic1111 en APIS.'},
    {'id': 'deepseek-v4-flash:cloud', 'name': 'DeepSeek V4 Flash Cloud', 'category':'chat', 'task': 'razonamiento/código cloud', 'ram_min_gb': 4, 'disk_gb': 0, 'local': False, 'vision': False, 'note': 'No se descarga localmente: es cloud. Requiere cuenta/API/conexión.'},
]

REQUIRED_LOW_RESOURCE_MODELS = [
    {"id": "gemma3:270m", "role": "chat", "why": "chat ultrarrápido por defecto"},
    {"id": "gemma3:1b", "role": "chat", "why": "chat rápido alternativo"},
    {"id": "llama3.2:1b", "role": "chat", "why": "chat rápido alternativo"},
    {"id": "qwen2.5-coder:0.5b", "role": "code", "why": "código ligero"},
    {"id": "moondream:latest", "role": "vision", "why": "visión ligera para cámara/pantalla/imágenes"},
    {"id": "gemma3:4b", "role": "vision", "why": "visión local más fuerte para pantalla/cámara"},
    {"id": "nomic-embed-text", "role": "embedding", "why": "memoria/búsqueda semántica local"}
]

_OLLAMA_STATUS_CACHE = {"ts": 0.0, "value": None}
_OLLAMA_MODELS_CACHE = {"ts": 0.0, "value": []}

def base_url():
    if get_setting:
        try:
            return (get_setting('ollama_base_url', DEFAULT_OLLAMA_BASE_URL) or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
        except Exception:
            return DEFAULT_OLLAMA_BASE_URL
    return DEFAULT_OLLAMA_BASE_URL

def ollama_executable():
    found = shutil.which('ollama') or shutil.which('ollama.exe')
    if found:
        return found
    candidates = []
    local = os.getenv('LOCALAPPDATA')
    program_files = os.getenv('ProgramFiles')
    program_files_x86 = os.getenv('ProgramFiles(x86)')
    home = str(Path.home())
    if local:
        candidates += [
            Path(local) / 'Programs' / 'Ollama' / 'ollama.exe',
            Path(local) / 'Ollama' / 'ollama.exe',
        ]
    if program_files:
        candidates.append(Path(program_files) / 'Ollama' / 'ollama.exe')
    if program_files_x86:
        candidates.append(Path(program_files_x86) / 'Ollama' / 'ollama.exe')
    candidates.append(Path(home) / 'AppData' / 'Local' / 'Programs' / 'Ollama' / 'ollama.exe')
    for c in candidates:
        try:
            if c.exists():
                return str(c)
        except Exception:
            pass
    return None

def server_ok(timeout=0.45):
    try:
        r = requests.get(f"{base_url()}/api/tags", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False

def start_ollama_background(wait=False):
    exe = ollama_executable()
    if not exe:
        return False
    try:
        subprocess.Popen(
            [exe, 'serve'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        )
        if wait:
            for _ in range(5):
                time.sleep(0.35)
                if server_ok(timeout=0.35):
                    return True
        return True
    except Exception:
        return False

def list_models(timeout=0.65, use_cache=True):
    now = time.time()
    if use_cache and _OLLAMA_MODELS_CACHE["value"] and now - _OLLAMA_MODELS_CACHE["ts"] < 3.0:
        return {"models": _OLLAMA_MODELS_CACHE["value"], "cached": True}
    try:
        r = requests.get(f"{base_url()}/api/tags", timeout=timeout)
        r.raise_for_status()
        data = r.json()
        models = data.get("models", [])
        _OLLAMA_MODELS_CACHE.update({"ts": now, "value": models})
        return {"models": models}
    except Exception as e:
        return {"models": [], "error": str(e)}

def installed_model_names():
    names = []
    for m in list_models(timeout=0.65).get("models", []):
        n = m.get("name") or m.get("model") or ""
        if n:
            names.append(n)
    return names

def normalize_model_name(name: str):
    name = (name or "").strip()
    if not name:
        return ""
    if ":" not in name:
        return name + ":latest"
    return name

def choose_chat_model(preferred: str | None = None):
    names = installed_model_names()
    if not names:
        return preferred or "gemma3:1b", False, []
    preferred = normalize_model_name(preferred or "gemma3:1b")
    if preferred in names:
        return preferred, True, names
    preferred_base = preferred.split(":")[0]
    for n in names:
        if n == preferred or n.split(":")[0] == preferred_base:
            return n, True, names

    # Prioriza modelos pequeños para velocidad real.
    priority = [
        "gemma3:270m", "gemma3:1b", "llama3.2:1b", "qwen3:0.6b",
        "qwen2.5-coder:0.5b", "qwen2.5-coder:1.5b",
        "llama3.2:3b", "gemma3:4b"
    ]
    for p in priority:
        for n in names:
            if n == p or n.split(":")[0] == p.split(":")[0]:
                return n, True, names
    return names[0], True, names

def status(fast=True):
    now = time.time()
    if fast and _OLLAMA_STATUS_CACHE["value"] and now - _OLLAMA_STATUS_CACHE["ts"] < 2.0:
        return _OLLAMA_STATUS_CACHE["value"]

    exe = ollama_executable()
    installed = bool(exe)
    running = server_ok(timeout=0.35)
    started = False

    if installed and not running:
        started = start_ollama_background(wait=False)
        time.sleep(0.12)
        running = server_ok(timeout=0.35)

    models = list_models(timeout=0.55).get('models', []) if running else []
    value = {
        'installed': installed,
        'running': running,
        'starting': bool(installed and started and not running),
        'base_url': base_url(),
        'ollama_executable': exe or '',
        'models': models,
        'hardware': get_hardware_profile()
    }
    _OLLAMA_STATUS_CACHE.update({"ts": now, "value": value})
    return value

def recommend_models():
    hw = get_hardware_profile()
    ram = hw.get('ram_gb') or 0
    free = hw.get('free_disk_gb') or 0
    tier = tier_from_ram(ram)
    installed = set(installed_model_names())
    installed_bases = {x.split(':')[0] for x in installed}
    rec = []
    for m in MODEL_CATALOG:
        ok_ram = (not ram) or ram >= m['ram_min_gb']
        ok_disk = (not free) or free >= max(2.0, m['disk_gb'] * 2)
        item = dict(m)
        item['recommended'] = bool(ok_ram and ok_disk)
        item['installed'] = bool(m['id'] in installed or m['id'].split(':')[0] in installed_bases)
        item['reason'] = 'Compatible según RAM/espacio detectado.' if item['recommended'] else (
            f"Necesita aprox. {m['ram_min_gb']} GB RAM; tu PC reporta {ram} GB."
            if not ok_ram else f"Necesita espacio libre; tu PC reporta {free} GB."
        )
        rec.append(item)
    return {'hardware': hw, 'tier': tier, 'models': rec}

def install_ollama_windows():
    return {
        'ok': True,
        'message': 'Si Ollama no está instalado, abre la descarga oficial. Si ya lo tienes, no lo instales de nuevo: pulsa Actualizar modelos.',
        'download_url': 'https://ollama.com/download/windows'
    }

def pull_model(model_id: str):
    model_id = (model_id or '').strip()
    if not model_id:
        return {'ok': False, 'message': 'Escribe un ID de modelo de Ollama.'}
    if any(tag in model_id for tag in [':api', ':cloud', ':local']):
        return {
            'ok': False,
            'model': model_id,
            'message': 'Este item no se descarga por Ollama. Configúralo en APIS o instala la herramienta local correspondiente.'
        }
    if not ollama_executable():
        return {'ok': False, 'message': 'Ollama no está instalado o ARKEA no lo encontró.', 'download_url': 'https://ollama.com/download/windows'}

    if not server_ok(timeout=0.55):
        start_ollama_background(wait=True)
    if not server_ok(timeout=0.55):
        return {
            'ok': False,
            'message': 'Ollama está instalado, pero su servidor local no respondió rápido en http://127.0.0.1:11434. Abre Ollama una vez y vuelve a intentar.'
        }

    try:
        installed = installed_model_names()
        bases = {n.split(':')[0] for n in installed}
        if model_id in installed or model_id.split(':')[0] in bases:
            return {'ok': True, 'already_installed': True, 'model': model_id, 'message': f'El modelo {model_id} ya está instalado. No lo descargué otra vez.'}
    except Exception:
        pass

    try:
        r = requests.post(f"{base_url()}/api/pull", json={'model': model_id, 'stream': False}, timeout=1800)
        r.raise_for_status()
        _OLLAMA_MODELS_CACHE.update({"ts": 0.0, "value": []})
        _OLLAMA_STATUS_CACHE.update({"ts": 0.0, "value": None})
        return {'ok': True, 'model': model_id, 'message': f'Modelo {model_id} descargado/actualizado correctamente.', 'result': r.json() if r.text else {}}
    except Exception as e:
        return {'ok': False, 'model': model_id, 'message': str(e)[:800]}

def default_models_for_this_pc():
    rec = recommend_models()
    models = [m for m in rec.get('models', []) if m.get('recommended') and m.get('local')]
    chosen = []
    for preferred in ['gemma3:270m', 'gemma3:1b', 'llama3.2:1b', 'qwen2.5-coder:0.5b', 'qwen2.5-coder:1.5b', 'gemma3:4b']:
        for m in models:
            if m['id'] == preferred and m['id'] not in chosen:
                chosen.append(m['id'])
    if not chosen:
        chosen = ['gemma3:270m']
    return chosen[:3]

def pull_default_models():
    if not ollama_executable():
        return {'ok': False, 'message': 'Primero instala Ollama.', 'models': []}
    if not server_ok(timeout=0.55):
        start_ollama_background(wait=True)
    if not server_ok(timeout=0.55):
        return {'ok': False, 'message': 'Ollama no está ejecutándose. Abre Ollama una vez y vuelve a intentar.', 'models': []}
    results = []
    for mid in default_models_for_this_pc():
        results.append(pull_model(mid))
    return {'ok': True, 'message': 'Proceso terminado.', 'models': results}

def _setting(key: str, default: str = ''):
    if get_setting:
        try:
            return get_setting(key, default) or default
        except Exception:
            return default
    return default

def installed_model_map():
    out = []
    for m in list_models(timeout=1.0).get('models', []):
        name = m.get('name') or m.get('model') or ''
        if name:
            out.append({'name': name, 'size': m.get('size'), 'modified_at': m.get('modified_at')})
    return out

def get_selected_models():
    return {
        'chat': _setting('preferred_model_chat', 'gemma3:270m'),
        'code': _setting('preferred_model_code', 'qwen2.5-coder:0.5b'),
        'vision': _setting('preferred_model_vision', 'moondream:latest'),
        'embedding': _setting('preferred_model_embedding', 'nomic-embed-text'),
        'stt': _setting('local_whisper_model', 'tiny')
    }

def fastest_installed(candidates=None):
    names = installed_model_names()
    if not names:
        return '', False
    candidates = candidates or ['gemma3:270m','gemma3:1b','llama3.2:1b','qwen3:0.6b','qwen2.5-coder:0.5b','qwen2.5-coder:1.5b','llama3.2:3b','gemma3:4b','moondream:latest']
    bases = {n.split(':')[0]: n for n in names}
    for c in candidates:
        if c in names: return c, True
        if c.split(':')[0] in bases: return bases[c.split(':')[0]], True
    return names[0], True

def warm_model(model_id: str | None = None):
    model_id = model_id or _setting('preferred_model_chat', 'gemma3:270m')
    chosen, ok, _ = choose_chat_model(model_id)
    if not ok:
        return {'ok': False, 'message': 'No hay modelo instalado para precargar.'}
    try:
        payload = {"model": chosen, "prompt": "ok", "stream": False, "options": {"num_predict": 1, "num_ctx": 512}}
        r = requests.post(f"{base_url()}/api/generate", json=payload, timeout=90)
        return {'ok': r.ok, 'model': chosen, 'status': r.status_code, 'message': 'Modelo precargado.' if r.ok else r.text[:300]}
    except Exception as e:
        return {'ok': False, 'model': chosen, 'message': str(e)[:400]}

def delete_model(model_id: str):
    model_id = (model_id or '').strip()
    if not model_id:
        return {'ok': False, 'message': 'Selecciona un modelo.'}
    try:
        r = requests.delete(f"{base_url()}/api/delete", json={'model': model_id}, timeout=90)
        _OLLAMA_MODELS_CACHE.update({'ts': 0.0, 'value': []})
        _OLLAMA_STATUS_CACHE.update({'ts': 0.0, 'value': None})
        return {'ok': r.ok, 'model': model_id, 'message': 'Modelo eliminado.' if r.ok else r.text[:500]}
    except Exception as e:
        return {'ok': False, 'model': model_id, 'message': str(e)[:500]}

def chat_local(message: str, system: str = "Eres ARKEA AI.", model: str | None = None):
    preferred = model or _setting('preferred_model_chat', 'gemma3:270m')

    st = status(fast=True)
    if not st.get('installed'):
        return "Ollama no está instalado todavía. ARKEA lo prepara en segundo plano; también puedes abrir Ajustes > Modelos."
    if not st.get('running'):
        start_ollama_background(wait=False)
        if not server_ok(timeout=0.8):
            return "Ollama está iniciando. ARKEA ya intentó levantar ollama serve; vuelve a enviar en unos segundos."

    chosen, has_model, installed = choose_chat_model(preferred)
    if not has_model:
        return "Aún no hay modelos instalados. ARKEA está descargando el pack mínimo automático."

    def call_model(mid, timeout_s=80, max_tokens=240):
        payload = {
            "model": mid,
            "stream": False,
            "messages": [
                {"role": "system", "content": system + "\nResponde útil, directo y en español. Si el usuario pide crear archivo, explica brevemente lo creado."},
                {"role": "user", "content": message}
            ],
            "options": {"num_predict": max_tokens, "num_ctx": 2048, "temperature": 0.28, "top_k": 30, "top_p": 0.88}
        }
        r = requests.post(f"{base_url()}/api/chat", json=payload, timeout=timeout_s)
        r.raise_for_status()
        return (r.json().get("message", {}) or {}).get("content", "").strip()

    # Usa modelo elegido; si tarda, fallback automático al ultrarrápido.
    try:
        return call_model(chosen, timeout_s=80, max_tokens=260) or "Listo."
    except requests.exceptions.Timeout:
        fast, ok = fastest_installed()
        if ok and fast != chosen:
            try:
                return call_model(fast, timeout_s=65, max_tokens=180) or "Listo."
            except Exception:
                pass
        return "El modelo local está cargando por primera vez. ARKEA seguirá usando el modelo más rápido disponible."
    except Exception as e:
        fast, ok = fastest_installed()
        if ok and fast != chosen:
            try:
                return call_model(fast, timeout_s=65, max_tokens=180) or "Listo."
            except Exception:
                pass
        return f"Ollama respondió con error local: {str(e)[:180]}"


def pull_required_models():
    """
    Pack mínimo gratuito y de pocos recursos. Se descarga automáticamente por Ollama.
    """
    if not ollama_executable():
        return {'ok': False, 'message': 'Ollama no está instalado. ARKEA intentará abrir/usar OllamaSetup incluido.', 'models': [], 'download_url': 'https://ollama.com/download/windows'}
    if not server_ok(timeout=0.8):
        start_ollama_background(wait=True)
    if not server_ok(timeout=1.2):
        return {'ok': False, 'message': 'Ollama está instalado, pero todavía no respondió. ARKEA lo seguirá intentando en segundo plano.', 'models': []}
    results = []
    for item in REQUIRED_LOW_RESOURCE_MODELS:
        try:
            results.append({'role': item['role'], 'why': item['why'], **pull_model(item['id'])})
        except Exception as e:
            results.append({'ok': False, 'role': item.get('role'), 'model': item.get('id'), 'message': str(e)[:500]})
    try:
        if upsert_setting:
            upsert_setting('preferred_model_chat', 'gemma3:270m')
            upsert_setting('preferred_model_code', 'qwen2.5-coder:0.5b')
            upsert_setting('preferred_model_vision', 'moondream:latest')
            upsert_setting('preferred_model_embedding', 'nomic-embed-text')
            upsert_setting('local_whisper_model', 'tiny')
        warm_model('gemma3:270m')
    except Exception:
        pass
    return {'ok': True, 'message': 'Pack mínimo procesado. Chat rápido por defecto: gemma3:270m. Puedes cambiarlo en Ajustes > Modelos.', 'models': results}

