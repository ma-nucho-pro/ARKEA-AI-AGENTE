# ARKEA AI - by: Arkeai AI Roberto Manuel Jara Peche
# Copyright (C) 2026 Roberto Manuel Jara Peche. Licensed under AGPL-3.0-or-later.
import os
import sys
import hmac
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from backend.arkea_core.db import init_db
from backend.arkea_core.skills import install_gemma_default_skill
from backend.routes import chat, projects, memory, skills, obsidian, image_lab, mcp_hub, research, settings, docs, voice, ollama, conversations, apis, vision, automation, uploads, files, omniroute

if os.getenv("ARKEA_BUNDLE_DIR"):
    BASE_DIR = Path(os.getenv("ARKEA_BUNDLE_DIR")).resolve()
elif getattr(sys, "frozen", False):
    BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)).resolve()
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = Path(os.getenv("ARKEA_DATA_DIR", str(BASE_DIR / "data"))).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
API_TOKEN = os.getenv("ARKEA_API_TOKEN", "")
PUBLIC_DATA_DIRS = {
    "generated": DATA_DIR / "generated",
    "uploads": DATA_DIR / "uploads" / "public",
}
for public_dir in PUBLIC_DATA_DIRS.values():
    public_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ARKEA AI OmniAgent Desktop", version="0.1.0")

@app.middleware("http")
async def local_security(request: Request, call_next):
    if API_TOKEN:
        supplied = request.headers.get("x-arkea-token", "")
        if not hmac.compare_digest(supplied, API_TOKEN):
            return JSONResponse({"detail": "Acceso local no autorizado"}, status_code=401)
    declared_size = request.headers.get("content-length")
    if declared_size:
        try:
            if int(declared_size) > 55 * 1024 * 1024:
                return JSONResponse({"detail": "Solicitud demasiado grande"}, status_code=413)
        except ValueError:
            return JSONResponse({"detail": "Content-Length no válido"}, status_code=400)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; media-src 'self' data: blob:; connect-src 'self' https://wttr.in; "
        "frame-src 'self' data: blob:; object-src 'none'; base-uri 'none'; form-action 'self'"
    )
    return response

@app.on_event("startup")
def startup():
    init_db()
    try:
        install_gemma_default_skill()
    except Exception:
        pass

app.include_router(settings.router)
app.include_router(apis.router)
app.include_router(omniroute.router)
app.include_router(chat.router)
app.include_router(projects.router)
app.include_router(memory.router)
app.include_router(skills.router)
app.include_router(obsidian.router)
app.include_router(image_lab.router)
app.include_router(mcp_hub.router)
app.include_router(research.router)
app.include_router(docs.router)
app.include_router(voice.router)
app.include_router(ollama.router)
app.include_router(conversations.router)
app.include_router(vision.router)
app.include_router(automation.router)
app.include_router(uploads.router)
app.include_router(files.router)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
for name, public_dir in PUBLIC_DATA_DIRS.items():
    app.mount(f"/data/{name}", StaticFiles(directory=str(public_dir)), name=f"data-{name}")

@app.get("/")
def index():
    p = FRONTEND_DIR / "index.html"
    if p.exists():
        return HTMLResponse(p.read_text(encoding="utf-8"))
    return HTMLResponse("""<!doctype html><html><body style='background:#030712;color:white;font-family:Arial;padding:30px'>
    <h1>ARKEA AI Desktop</h1><p>Backend activo, pero no encontré frontend/index.html.</p></body></html>""")

@app.get("/api/health")
def health():
    return {"ok": True, "name": "ARKEA AI Desktop", "edition": "OmniAgent", "version": "0.1.0"}
