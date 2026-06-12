import os, json, re, shutil
from pathlib import Path
from backend.arkea_core.db import execute, rows, one

SKILLS_ROOT = Path(os.getenv("ARKEA_DATA_DIR", "./data")) / "skills"
SKILLS_ROOT.mkdir(parents=True, exist_ok=True)

def slugify(text: str):
    return re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")[:60] or "skill"

def create_skill_from_prompt(prompt: str):
    raw_name = prompt.replace("create skill", "").replace("crear skill", "").strip() or "Nueva skill"
    skill_id = slugify(raw_name)
    folder = SKILLS_ROOT / skill_id
    folder.mkdir(parents=True, exist_ok=True)
    title = raw_name[:80]
    md = f"""# Skill: {title}

## Objetivo
Crear una habilidad especializada para: {raw_name}.

## Cuándo usarla
Usar cuando el usuario pida tareas relacionadas con: {raw_name}.

## Flujo recomendado
1. Analizar la solicitud del usuario.
2. Revisar memoria de la skill y del proyecto actual.
3. Crear o modificar archivos dentro del workspace.
4. Mostrar resultado en el visualizador.
5. Guardar historial y versiones.

## Herramientas permitidas
- read_project_file
- write_project_file
- create_project
- preview_file
- save_memory

## Reglas de memoria
Usar primero memoria del proyecto activo. Usar memoria global solo si ayuda. Guardar aprendizajes en scope=skill:{skill_id}.
"""
    manifest = {
        "id": skill_id,
        "name": title,
        "description": f"Skill creada desde prompt: {raw_name}",
        "permissions": ["workspace.read", "workspace.write", "preview.write", "memory.write"],
        "entry": "skill.md"
    }
    (folder / "skill.md").write_text(md, encoding="utf-8")
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    execute("INSERT OR REPLACE INTO skills(skill_id,name,description,folder_path,permissions) VALUES(?,?,?,?,?)",
            (skill_id, title, manifest["description"], str(folder), json.dumps(manifest["permissions"])))
    return manifest

def list_skills():
    return rows("SELECT * FROM skills ORDER BY created_at DESC")

def install_markdown_skill(name: str, markdown: str):
    skill_id = slugify(name)
    folder = SKILLS_ROOT / skill_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "skill.md").write_text(markdown, encoding="utf-8")
    manifest = {"id": skill_id, "name": name, "description": "Skill instalada desde Markdown", "permissions": ["workspace.read", "workspace.write"]}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    execute("INSERT OR REPLACE INTO skills(skill_id,name,description,folder_path,permissions) VALUES(?,?,?,?,?)",
            (skill_id, name, manifest["description"], str(folder), json.dumps(manifest["permissions"])))
    return manifest

def load_skill(skill_id: str):
    row = one("SELECT * FROM skills WHERE skill_id=?", (skill_id,))
    if not row:
        return None
    folder = Path(row["folder_path"])
    md = (folder / "skill.md").read_text(encoding="utf-8") if (folder / "skill.md").exists() else ""
    row["markdown"] = md
    return row


GEMMA_DEFAULT_SKILL_MD = """# Skill: Gemma Dev Agent

## Origen
Integración local inspirada en el paquete público `google-gemma/gemma-skills`.
Comandos de referencia compartidos por el usuario:

```bash
npx skills add google-gemma/gemma-skills --list
npx ctx7 skills install /google-gemma/gemma-skills
```

## Objetivo
Acelerar agentes basados en Gemma/Gemma 4 para construir, analizar y modificar proyectos con una estrategia clara.

## Cuándo usarla
Usar esta skill cuando el usuario pida:
- crear o mejorar una app, web, juego, dashboard o agente;
- trabajar con Gemma, Ollama, modelos locales o APIs;
- generar código, corregir bugs, explicar pantalla/cámara o crear archivos;
- dividir un objetivo grande en subtareas rápidas.

## Flujo recomendado
1. Entender la intención principal del usuario.
2. Detectar si la tarea es chat, código, visión, documento, imagen, voz o automatización.
3. Usar el modelo local más ligero disponible para responder rápido.
4. Para código, preferir modelos coder pequeños si existen.
5. Para visión, usar moondream, gemma3:4b, llava o una API de visión.
6. Crear resultado visual HTML cuando ayude a verificar el trabajo.
7. Guardar archivos siempre en la carpeta del chat/proyecto activo.
8. Si falta una dependencia, indicar cómo instalarla y continuar con una alternativa.

## Reglas de velocidad
- Primero responder rápido con lo esencial.
- No bloquear la interfaz por tareas largas.
- Las descargas de modelos van en segundo plano.
- Evitar repetir descargas ya instaladas.
- Si un modelo tarda, cambiar a uno más pequeño.

## Herramientas permitidas
- create_project
- write_project_file
- preview_file
- save_memory
- analyze_image
- transcribe_audio
- pull_ollama_model
- install_required_pack

## Resultado esperado
ARKEA debe producir respuestas accionables, archivos reales y vista previa visual cuando sea posible.
"""

def install_gemma_default_skill():
    return install_markdown_skill('Gemma Dev Agent', GEMMA_DEFAULT_SKILL_MD)
