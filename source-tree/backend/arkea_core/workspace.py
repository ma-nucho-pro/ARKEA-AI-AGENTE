import os, re, json
from pathlib import Path
from backend.arkea_core.db import execute, one, rows
from backend.arkea_core.security import safe_path

DEFAULT_WORKSPACE = Path(os.getenv("ARKEA_WORKSPACE", "./data/projects"))

def slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]+", "-", name.strip().lower()).strip("-")
    return s[:60] or "proyecto"

def get_workspace() -> Path:
    setting = one("SELECT value FROM settings WHERE key='workspace'")
    path = Path(setting["value"] if setting else str(DEFAULT_WORKSPACE))
    path.mkdir(parents=True, exist_ok=True)
    return path

def create_project(name: str, type_: str = "general"):
    workspace = get_workspace()
    folder = workspace / slugify(name)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "project.json").write_text(json.dumps({"name": name, "type": type_}, indent=2, ensure_ascii=False), encoding="utf-8")
    project_id = execute("INSERT INTO projects(name,type,folder_path,active) VALUES(?,?,?,1)", (name, type_, str(folder)))
    return {"id": project_id, "name": name, "type": type_, "folder_path": str(folder)}

def write_project_file(project_id: int, relpath: str, content: str, file_type: str = "text"):
    p = one("SELECT * FROM projects WHERE id=?", (project_id,))
    if not p:
        raise ValueError("Proyecto no encontrado")
    target = safe_path(p["folder_path"], relpath)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    execute("INSERT INTO project_files(project_id,file_path,file_type) VALUES(?,?,?)", (project_id, str(target), file_type))
    return str(target)

def set_preview(project_id: int, path: str):
    execute("UPDATE projects SET preview_path=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (path, project_id))

def list_projects():
    return rows("SELECT * FROM projects ORDER BY updated_at DESC, id DESC")
