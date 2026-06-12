# ARKEA AI - by: Arkeai AI Roberto Manuel Jara Peche
# Copyright (C) 2026 Roberto Manuel Jara Peche. Licensed under AGPL-3.0-or-later.
import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from backend.arkea_core.db import init_db
from backend.arkea_core.skills import install_gemma_default_skill
from backend.routes import chat, projects, memory, skills, obsidian, image_lab, mcp_hub, research, settings, docs, voice, ollama, conversations, apis, vision, automation, uploads, files

if os.getenv("ARKEA_BUNDLE_DIR"):
    BASE_DIR = Path(os.getenv("ARKEA_BUNDLE_DIR")).resolve()
elif getattr(sys, "frozen", False):
    BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)).resolve()
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = Path(os.getenv("ARKEA_DATA_DIR", str(BASE_DIR / "data"))).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ARKEA AI Desktop", version="0.8.0")

@app.on_event("startup")
def startup():
    init_db()
    try:
        install_gemma_default_skill()
    except Exception:
        pass

app.include_router(settings.router)
app.include_router(apis.router)
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
if DATA_DIR.exists():
    app.mount("/data", StaticFiles(directory=str(DATA_DIR)), name="data")

@app.get("/")
def index():
    p = FRONTEND_DIR / "index.html"
    if p.exists():
        return FileResponse(p)
    return HTMLResponse("""<!doctype html><html><body style='background:#030712;color:white;font-family:Arial;padding:30px'>
    <h1>ARKEA AI Desktop</h1><p>Backend activo, pero no encontré frontend/index.html.</p></body></html>""")

@app.get("/api/health")
def health():
    return {"ok": True, "name": "ARKEA AI Desktop", "version": "0.8.0", "base_dir": str(BASE_DIR), "data_dir": str(DATA_DIR)}
