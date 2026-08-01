from fastapi import APIRouter
from pydantic import BaseModel, Field
from backend.arkea_core.db import rows, execute
from backend.arkea_core.secrets import is_sensitive_key

router = APIRouter(prefix="/api/arkea/settings", tags=["settings"])

class SettingIn(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: str = Field(max_length=8_000_000)

@router.get("")
def get_settings():
    settings = rows("SELECT key,value,updated_at FROM settings ORDER BY key")
    for setting in settings:
        if is_sensitive_key(setting["key"]):
            setting["configured"] = bool(setting.get("value"))
            setting["value"] = ""
    return {"settings": settings}

@router.post("/set")
def set_setting(body: SettingIn):
    if is_sensitive_key(body.key) and not body.value:
        return {"ok": True, "preserved": True}
    execute("INSERT OR REPLACE INTO settings(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)", (body.key, body.value))
    return {"ok": True}


class BulkSettingsIn(BaseModel):
    values: dict

@router.post("/bulk")
def bulk_set(body: BulkSettingsIn):
    saved = 0
    for k, v in (body.values or {}).items():
        if len(str(k)) > 100 or len(str(v)) > 8_000_000:
            continue
        if is_sensitive_key(k) and not v:
            continue
        execute("INSERT OR REPLACE INTO settings(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)", (str(k), str(v)))
        saved += 1
    return {"ok": True, "saved": saved}
