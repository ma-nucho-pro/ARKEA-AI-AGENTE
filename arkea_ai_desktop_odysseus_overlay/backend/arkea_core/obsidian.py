import os, re
from pathlib import Path
from datetime import datetime
from backend.arkea_core.db import one, execute

DEFAULT_VAULT = Path(os.getenv("ARKEA_OBSIDIAN_VAULT", "./data/obsidian_vault"))
ALLOWED_SECTIONS = {
    "00_Global", "01_Projects", "02_Skills", "03_Research",
    "04_Generated", "05_History",
}

def slug(s: str):
    return re.sub(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]+", "-", s.strip().lower()).strip("-") or "nota"

def get_vault():
    setting = one("SELECT value FROM settings WHERE key='obsidian_vault'")
    vault = Path(setting["value"] if setting else str(DEFAULT_VAULT))
    vault.mkdir(parents=True, exist_ok=True)
    for folder in sorted(ALLOWED_SECTIONS):
        (vault / folder).mkdir(exist_ok=True)
    return vault

def write_note(section: str, title: str, content: str):
    if section not in ALLOWED_SECTIONS:
        raise ValueError("Sección de Obsidian no permitida")
    if not isinstance(title, str) or not title.strip() or len(title) > 200:
        raise ValueError("Título de nota no válido")
    if not isinstance(content, str) or not content.strip() or len(content) > 2_000_000:
        raise ValueError("Contenido de nota no válido")
    vault = get_vault()
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{slug(title)}.md"
    path = vault / section / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    md = f"# {title}\n\n{content}\n"
    path.write_text(md, encoding="utf-8")
    return str(path)

def configure_vault(path: str):
    if not isinstance(path, str) or not path.strip() or len(path) > 1_000:
        raise ValueError("Ruta de vault no válida")
    execute("INSERT OR REPLACE INTO settings(key,value,updated_at) VALUES('obsidian_vault',?,CURRENT_TIMESTAMP)", (path,))
    return str(get_vault())
