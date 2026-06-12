from fastapi import APIRouter
from pydantic import BaseModel
from backend.arkea_core.db import rows, execute

router = APIRouter(prefix="/api/arkea/settings", tags=["settings"])

class SettingIn(BaseModel):
    key: str
    value: str

@router.get("")
def get_settings():
    return {"settings": rows("SELECT key,value,updated_at FROM settings ORDER BY key")}

@router.post("/set")
def set_setting(body: SettingIn):
    execute("INSERT OR REPLACE INTO settings(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)", (body.key, body.value))
    return {"ok": True}


class BulkSettingsIn(BaseModel):
    values: dict

@router.post("/bulk")
def bulk_set(body: BulkSettingsIn):
    for k, v in (body.values or {}).items():
        execute("INSERT OR REPLACE INTO settings(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)", (str(k), str(v)))
    return {"ok": True, "saved": len(body.values or {})}
