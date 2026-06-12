import os, re
from pathlib import Path
from datetime import datetime
from backend.arkea_core.db import one, execute

DEFAULT_VAULT = Path(os.getenv("ARKEA_OBSIDIAN_VAULT", "./data/obsidian_vault"))

def slug(s: str):
    return re.sub(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]+", "-", s.strip().lower()).strip("-") or "nota"

def get_vault():
    setting = one("SELECT value FROM settings WHERE key='obsidian_vault'")
    vault = Path(setting["value"] if setting else str(DEFAULT_VAULT))
    vault.mkdir(parents=True, exist_ok=True)
    for folder in ["00_Global", "01_Projects", "02_Skills", "03_Research", "04_Generated", "05_History"]:
        (vault / folder).mkdir(exist_ok=True)
    return vault

def write_note(section: str, title: str, content: str):
    vault = get_vault()
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{slug(title)}.md"
    path = vault / section / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    md = f"# {title}\n\n{content}\n"
    path.write_text(md, encoding="utf-8")
    return str(path)

def configure_vault(path: str):
    execute("INSERT OR REPLACE INTO settings(key,value,updated_at) VALUES('obsidian_vault',?,CURRENT_TIMESTAMP)", (path,))
    return str(get_vault())
