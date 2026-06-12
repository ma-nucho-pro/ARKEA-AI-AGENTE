# Guía para aplicar ARKEA AI Desktop encima de Odysseus

1. Clona Odysseus:

```bash
git clone https://github.com/pewdiepie-archdaemon/odysseus.git
cd odysseus
git checkout -b arkea-ai-desktop
```

2. Copia este overlay dentro del repo o en una carpeta vecina.

3. Ejecuta:

```bash
python ../arkea_ai_desktop_odysseus_overlay/patch_into_odysseus.py --odysseus .
```

4. Si `app.py` cambió, registra manualmente las rutas ARKEA:

```python
from backend.arkea_app import app as arkea_app
```

O usa el modo standalone de ARKEA mientras adaptas la UI original de Odysseus.

## Estrategia recomendada

No borres el backend de Odysseus. Agrega ARKEA como capa:

- `frontend/` para la UI ARKEA.
- `backend/arkea_core/` para memoria, skills, workspace y research.
- `backend/routes/` para APIs ARKEA.
- `desktop/` para Electron.

Luego fusiona con los módulos existentes de Odysseus: memory, MCP, skills, shell, files, image editor y settings.
