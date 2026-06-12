from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from backend.arkea_core.workspace import create_project, list_projects, write_project_file
from backend.arkea_core.db import one

router = APIRouter(prefix="/api/arkea/projects", tags=["projects"])

class ProjectIn(BaseModel):
    name: str
    type: str = "general"

class FileIn(BaseModel):
    project_id: int
    path: str
    content: str
    file_type: str = "text"

@router.get("")
def get_projects():
    return {"projects": list_projects()}

@router.post("/create")
def create(body: ProjectIn):
    return create_project(body.name, body.type)

@router.post("/write")
def write_file(body: FileIn):
    return {"path": write_project_file(body.project_id, body.path, body.content, body.file_type)}

@router.get("/{project_id}/preview")
def preview(project_id: int):
    p = one("SELECT preview_path FROM projects WHERE id=?", (project_id,))
    if not p or not p.get("preview_path"):
        raise HTTPException(status_code=404, detail="Proyecto sin preview")
    path = Path(p["preview_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo preview no existe")
    return FileResponse(path)
