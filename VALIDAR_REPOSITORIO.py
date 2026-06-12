from __future__ import annotations

import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIRED = [
    ROOT / ".github" / "workflows" / "build-windows.yml",
    ROOT / "build_windows_installer.ps1",
    ROOT / "CREAR_EXE_ARKEA_AI.cmd",
    ROOT / "LICENSE",
    ROOT / "NOTICE",
    ROOT / "AUTHORS.md",
    ROOT / "arkea_ai_desktop_odysseus_overlay" / "patch_into_odysseus.py",
    ROOT / "arkea_ai_desktop_odysseus_overlay" / "requirements.txt",
    ROOT / "arkea_ai_desktop_odysseus_overlay" / "backend" / "arkea_app.py",
    ROOT / "arkea_ai_desktop_odysseus_overlay" / "frontend" / "index.html",
    ROOT / "arkea_ai_desktop_odysseus_overlay" / "frontend" / "app.js",
    ROOT / "arkea_ai_desktop_odysseus_overlay" / "desktop" / "main.js",
    ROOT / "arkea_ai_desktop_odysseus_overlay" / "desktop" / "package.json",
]

errors: list[str] = []

for path in REQUIRED:
    if not path.exists():
        errors.append(f"Falta: {path.relative_to(ROOT)}")

for path in ROOT.rglob("*.json"):
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"JSON inválido {path.relative_to(ROOT)}: {exc}")

for path in ROOT.rglob("*.py"):
    if any(part in {"_work", "release", ".venv", "node_modules"} for part in path.parts):
        continue
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception as exc:
        errors.append(f"Python inválido {path.relative_to(ROOT)}: {exc}")

try:
    import yaml  # type: ignore
except Exception:
    print("AVISO: instala PyYAML para validar YAML: python -m pip install pyyaml")
else:
    workflow = ROOT / ".github" / "workflows" / "build-windows.yml"
    if workflow.exists():
        try:
            yaml.safe_load(workflow.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"YAML inválido: {exc}")

if errors:
    print("VALIDACIÓN CON ERRORES")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("VALIDACIÓN ESTRUCTURAL CORRECTA")
print("La compilación final debe comprobarse en Windows o GitHub Actions.")
