# ARKEA AI

**Agente de escritorio open source, local-first y multimodal para Windows.**

ARKEA AI combina una aplicación de escritorio Electron, un backend FastAPI, modelos locales mediante Ollama y APIs compatibles con OpenAI/OpenRouter. El proyecto incluye chat, voz, visión, archivos, memoria local, skills, MCP, proyectos por carpetas, generación de documentos y vista previa visual.

**Autor:** Roberto Manuel Jara Peche  
**Marca:** Arkeai AI  
**Crédito:** `by: Arkeai AI Roberto Manuel Jara Peche`

## Características incluidas

- Chat por texto con historial y carpetas por proyecto.
- Entrada y respuesta por voz.
- Cámara, captura de pantalla y análisis de imágenes cuando existe un modelo de visión configurado.
- Modelos locales mediante Ollama y APIs externas mediante OpenRouter/OpenAI-compatible.
- Generación de HTML, Word, Excel, PowerPoint, SVG, código y proyectos locales.
- Vista previa de artefactos y apertura de la carpeta del proyecto.
- Memoria local, Obsidian, skills Markdown y MCP Hub.
- Configuración de ElevenLabs, OpenRouter, OpenAI y proveedores compatibles.
- Interfaz Jade Glass/Aero Glass con fondos y personaje personalizables.
- Builder para Windows y workflow de GitHub Actions.

## Estructura principal

```text
ARKEA-AI-AGENTE/
├── .github/workflows/build-windows.yml
├── arkea_ai_desktop_odysseus_overlay/
│   ├── backend/
│   ├── frontend/
│   ├── desktop/
│   ├── config/
│   ├── data/skills/
│   ├── scripts/
│   ├── patch_into_odysseus.py
│   ├── requirements.txt
│   └── start_arkea.py
├── build_windows_installer.ps1
├── CREAR_EXE_ARKEA_AI.cmd
├── .env.example
├── LICENSE
├── NOTICE
└── AUTHORS.md
```

## Subir el proyecto completo a GitHub

1. Extrae el ZIP.
2. Abre la carpeta `ARKEA-AI-AGENTE`.
3. Sube **todo el contenido de esa carpeta** a la raíz del repositorio.
4. Comprueba que GitHub muestre directamente:

```text
.github/
arkea_ai_desktop_odysseus_overlay/
build_windows_installer.ps1
CREAR_EXE_ARKEA_AI.cmd
README.md
```

No subas una carpeta adicional por encima de esos archivos.

## Crear el EXE en GitHub Actions

1. Abre la pestaña **Actions** del repositorio.
2. Selecciona **Build Windows Installer**.
3. Pulsa **Run workflow**.
4. Espera a que el trabajo termine en verde.
5. Descarga el artefacto `ARKEA-AI-Windows-x64`.

El workflow usa un runner de Windows, configura Python y Node.js, ejecuta `build_windows_installer.ps1` y publica el contenido de `release/` como artifact.

## Crear el EXE en tu PC

En Windows, ejecuta con doble clic:

```text
CREAR_EXE_ARKEA_AI.cmd
```

O desde CMD:

```cmd
CREAR_EXE_ARKEA_AI.cmd
```

El resultado se guarda en:

```text
release/
```

## Requisitos para compilación local

- Windows 10 u 11 de 64 bits.
- Git.
- Python 3.11 de 64 bits.
- Node.js 22 de 64 bits.
- Conexión a internet durante la primera compilación.

## APIs y secretos

Nunca publiques claves reales. Copia `.env.example` a `.env` únicamente en tu PC y completa allí las claves que uses.

```env
OPENROUTER_API_KEY=
OPENAI_API_KEY=
OPENAI_IMAGE_API_KEY=
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

El archivo `.env` está excluido por `.gitignore`.

## Modelos locales

ARKEA AI puede conectarse a Ollama en:

```text
http://127.0.0.1:11434
```

Los modelos no se incluyen físicamente en este repositorio por su gran tamaño. La aplicación puede detectarlos y descargarlos mediante Ollama según la configuración disponible.

## Validación rápida

Desde la raíz del proyecto:

```cmd
python VALIDAR_REPOSITORIO.py
```

La validación revisa la estructura, JSON, YAML, Python y archivos esenciales. No sustituye una compilación real de Windows.

## Licencia

ARKEA AI se distribuye bajo **AGPL-3.0-or-later** porque deriva e integra trabajo basado en Odysseus. Conserva `LICENSE`, `NOTICE` y `AUTHORS.md` en cualquier copia o modificación.

Odysseus: https://github.com/pewdiepie-archdaemon/odysseus

## Seguridad

- No publiques `.env`.
- No publiques bases de datos locales.
- No publiques archivos subidos por usuarios.
- No publiques claves API.
- Revisa los permisos antes de activar automatización del ordenador o MCPs externos.

## Autor

**by: Arkeai AI Roberto Manuel Jara Peche**
