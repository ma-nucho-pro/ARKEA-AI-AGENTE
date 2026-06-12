# Arkea AI — Odysseus Overlay / Starter Kit

Este ZIP es una **base funcional en Python/FastAPI** para convertir Odysseus en **Arkea AI**: agente local con memoria, proyectos, skills Markdown, MCP Hub, Obsidian Vault, visualizador en vivo, modo HTML visual, investigación legal para tesis, generación/edición de imágenes por máscara y conectores ampliables para video, logos y motion graphics.

> Importante: este paquete es un **overlay** para partir de Odysseus, no una copia completa del repositorio original. Primero clona Odysseus y luego aplica este overlay.

## Lo que incluye

- Backend local FastAPI.
- Base SQLite local (`data/arkea.db`).
- Memoria separada por ámbito: global, proyecto, skill, temporal y Obsidian.
- Skills en Markdown instalables/subibles.
- Creador de skills: `create skill ...`.
- Skill de tesis con estructura académica.
- Conectores legales de investigación: OpenAlex, Crossref, arXiv, Semantic Scholar/Unpaywall extensibles.
- Bloqueo explícito de Sci-Hub por riesgo de infracción de copyright.
- Workspace local tipo Codex.
- Visualizador HTML/imagen/proyecto.
- Image Lab: generación simulada/local y edición por máscara preparada para ComfyUI u otra API.
- MCP Hub para registrar servidores MCP.
- Obsidian Vault local para memoria visible.
- Frontend estilo ARKEA con voz del navegador.
- Electron starter para empaquetar como `.exe`, `.dmg`, `.AppImage`.

## Instalación rápida standalone

```bash
cd arkea_ai_desktop_odysseus_overlay
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate
pip install -r requirements.txt
python start_arkea.py
```

Abre:

```txt
http://127.0.0.1:7210
```

## Instalación encima de Odysseus

```bash
git clone https://github.com/pewdiepie-archdaemon/odysseus.git
cd odysseus
python ../arkea_ai_desktop_odysseus_overlay/patch_into_odysseus.py --odysseus .
```

Luego revisa `ODYSSEUS_PATCH_GUIDE.md` dentro de este ZIP para registrar rutas si tu versión de Odysseus cambió.

## Carpeta local de trabajo

Por defecto crea:

```txt
./data/projects/
./data/skills/
./data/obsidian_vault/
./data/generated/
```

Puedes cambiarlo desde Ajustes o editando `config/settings.example.json`.

## Sobre Sci-Hub

No se incluye integración con Sci-Hub. ARKEA bloquea ese conector y propone rutas legales: OpenAlex, Crossref, arXiv, CORE, DOAJ, PubMed, Semantic Scholar y Unpaywall. Puedes crear una skill de tesis que investigue con fuentes abiertas, DOIs, repositorios universitarios y artículos open access.

## Primeras pruebas

En el chat prueba:

```txt
create skill para hacer tesis con estructura UCV y matriz de consistencia
```

```txt
Crea una página web visual que explique memoria local y vectorial
```

```txt
Quiero crear una miniatura para YouTube sobre IA para docentes
```

```txt
Crea un proyecto de juego HTML simple de carreras 3D
```
