from fastapi import APIRouter
from pydantic import BaseModel
from backend.arkea_core import ollama
from backend.arkea_core.db import execute

router = APIRouter(prefix="/api/arkea/ollama", tags=["ollama"])

class PullIn(BaseModel):
    model_id: str | None = None
    model: str | None = None

class ModelPrefsIn(BaseModel):
    chat: str | None = None
    code: str | None = None
    vision: str | None = None
    embedding: str | None = None
    stt: str | None = None

@router.get("/status")
def status():
    return ollama.status()

@router.get("/recommend")
def recommend():
    return ollama.recommend_models()

@router.get("/catalog")
def catalog():
    st = ollama.status()
    rec = ollama.recommend_models()
    installed = set([(m.get('name') or m.get('model') or '') for m in st.get('models', [])])
    installed_bases = set([x.split(':')[0] for x in installed])
    catalog = []
    for m in rec['models']:
        catalog.append({
            'model_id': m['id'], 'title': m['name'], 'category': m.get('category') or m.get('task'), 'notes': m.get('note'),
            'recommended_ram_gb': m.get('ram_min_gb'), 'disk_gb': m.get('disk_gb'),
            'recommended_for_this_pc': 1 if m.get('recommended') else 0,
            'installed': 1 if (m['id'] in installed or m['id'].split(':')[0] in installed_bases) else 0,
            'reason': m.get('reason')
        })
    return {'specs': st.get('hardware'), 'tier': {'tier': rec.get('tier'), 'message': 'Recomendación según RAM y espacio detectado.'}, 'ollama': {'running': st.get('running'), 'installed': st.get('installed'), 'models': st.get('models')}, 'selected': ollama.get_selected_models(), 'catalog': catalog}

@router.post("/install")
def install():
    return ollama.install_ollama_windows()

@router.post("/pull")
def pull(body: PullIn):
    return ollama.pull_model(body.model_id or body.model or '')

@router.post('/pull-defaults')
def pull_defaults():
    return ollama.pull_default_models()


@router.get("/quick-status")
def quick_status():
    return ollama.status(fast=True)

@router.post("/refresh")
def refresh():
    try:
        ollama._OLLAMA_STATUS_CACHE.update({"ts": 0.0, "value": None})
        ollama._OLLAMA_MODELS_CACHE.update({"ts": 0.0, "value": []})
    except Exception:
        pass
    return ollama.status(fast=False)


@router.post("/pull-required")
def pull_required():
    return ollama.pull_required_models()


@router.get("/models/installed")
def installed_models():
    return {"models": ollama.installed_model_map(), "selected": ollama.get_selected_models()}

@router.post("/models/select")
def select_models(body: ModelPrefsIn):
    values = {
        'preferred_model_chat': body.chat,
        'preferred_model_code': body.code,
        'preferred_model_vision': body.vision,
        'preferred_model_embedding': body.embedding,
        'local_whisper_model': body.stt,
    }
    saved = 0
    for k,v in values.items():
        if v:
            execute("INSERT OR REPLACE INTO settings(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)", (k, v))
            saved += 1
    return {"ok": True, "saved": saved, "selected": ollama.get_selected_models()}

@router.post("/models/delete")
def delete_model(body: PullIn):
    return ollama.delete_model(body.model_id or body.model or '')

@router.post("/models/warm")
def warm_model(body: PullIn):
    return ollama.warm_model(body.model_id or body.model or None)
