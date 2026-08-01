from fastapi import APIRouter
from pydantic import BaseModel
from backend.arkea_core.db import get_setting, upsert_setting

router = APIRouter(prefix='/api/arkea/automation', tags=['automation'])

class PermissionIn(BaseModel):
    enabled: bool = False

@router.get('/status')
def status():
    return {
        'computer_control_enabled': get_setting('computer_control_enabled','0') == '1',
        'browser_agent_enabled': get_setting('browser_agent_enabled','0') == '1',
        'message': 'Modo seguro: ARKEA pedirá confirmación antes de controlar apps, navegador, cuentas, correo, compras o acciones sensibles.'
    }

@router.post('/computer-control')
def set_control(body: PermissionIn):
    upsert_setting('computer_control_enabled', '1' if body.enabled else '0')
    return {'ok': True, 'enabled': body.enabled}

@router.post('/browser-agent')
def set_browser_agent(body: PermissionIn):
    upsert_setting('browser_agent_enabled', '1' if body.enabled else '0')
    return {'ok': True, 'enabled': body.enabled}
