# Contribuir a ARKEA AI OmniAgent

Gracias por contribuir. Este repositorio acepta correcciones, pruebas,
documentación, nuevas skills, integraciones MCP y mejoras de accesibilidad o
compatibilidad con modelos.

## Estructura

- `arkea_ai_desktop_odysseus_overlay/`: código mantenido por ARKEA; aquí se
  realizan normalmente los cambios.
- `source-tree/`: árbol fuente correspondiente exacto de la versión publicada.
- `build_windows_installer.ps1`: constructor reproducible de Windows.
- `tools/`: utilidades de preparación y publicación.

No edites únicamente `_work/`, `release/`, `node_modules/` o un entorno virtual:
son resultados locales ignorados por Git.

## Preparar el entorno

```powershell
cd arkea_ai_desktop_odysseus_overlay
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install pytest
cd desktop
npm ci
```

## Pruebas obligatorias

```powershell
cd arkea_ai_desktop_odysseus_overlay
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
cd desktop
npm audit --omit=dev
```

Antes de proponer un cambio en Electron o el backend congelado, crea también el
instalador con `0_1_CREAR_EXE_OMNIAGENT.cmd`.

## Pull requests

1. Crea una rama corta y descriptiva.
2. Mantén cada PR enfocado en un problema.
3. Incluye pruebas para cambios funcionales o de seguridad.
4. Explica qué cambió, cómo se verificó y cualquier limitación restante.
5. No incluyas secretos, datos personales, bases de datos ni binarios generados.

## Seguridad

No publiques vulnerabilidades explotables en un issue público. Sigue el proceso
descrito en [SECURITY.md](SECURITY.md). Mantén la confirmación de herramientas
MCP activada salvo que el permiso sea deliberadamente seguro y acotado.
