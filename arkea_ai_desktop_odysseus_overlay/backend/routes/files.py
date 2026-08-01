from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
import os
from backend.arkea_core.workspace import get_workspace
from backend.arkea_core.db import one

router = APIRouter(prefix="/api/arkea/files", tags=["files"])

def _allowed_roots():
    roots = [get_workspace(), Path(os.getenv("ARKEA_DATA_DIR", "./data")).resolve()]
    try:
        setting = one("SELECT value FROM settings WHERE key='workspace'")
        if setting and setting.get('value'):
            roots.append(Path(setting['value']).expanduser().resolve())
    except Exception:
        pass
    # conversation folders are inside workspace, but allow user data dir too.
    out = []
    for r in roots:
        try:
            r.mkdir(parents=True, exist_ok=True)
            out.append(r.resolve())
        except Exception:
            pass
    return out

def _is_allowed(path: Path):
    rp = path.expanduser().resolve()
    for root in _allowed_roots():
        try:
            rp.relative_to(root)
            return True
        except Exception:
            continue
    return False

@router.get('/download')
def download(path: str = Query(...)):
    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_file():
        raise HTTPException(404, 'Archivo no encontrado')
    if not _is_allowed(p):
        raise HTTPException(403, 'Ruta no permitida')
    return FileResponse(str(p), filename=p.name)
