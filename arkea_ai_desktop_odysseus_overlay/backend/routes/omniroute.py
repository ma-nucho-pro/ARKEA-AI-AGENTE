from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.arkea_core import omniroute


router = APIRouter(prefix="/api/arkea/omniroute", tags=["omniroute"])


class ConfigureIn(BaseModel):
    mode: str = Field(default="auto", pattern="^(auto|free|local|direct)$")
    base_url: str | None = Field(default=None, max_length=300)
    api_key: str | None = Field(default=None, max_length=2_000)
    models: dict[str, str] = {}


@router.get("/status")
def get_status():
    return {"ok": True, "gateway": omniroute.status(), "settings": omniroute.settings()}


@router.get("/models")
def get_models():
    try:
        return {"ok": True, "models": omniroute.models()}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"OmniRoute no está disponible: {str(exc)[:240]}")


@router.post("/configure")
def configure(body: ConfigureIn):
    try:
        return {"ok": True, "settings": omniroute.configure(
            mode=body.mode,
            base_url=body.base_url,
            key=body.api_key,
            models_by_task=body.models,
        )}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/apply")
def apply_connections():
    return omniroute.apply_connections()

