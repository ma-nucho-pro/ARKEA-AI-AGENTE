# ARKEA AI

**ARKEA AI** es un agente de inteligencia artificial de escritorio, open source y multimodal, diseñado para crear, visualizar, editar y automatizar contenido digital desde una sola interfaz moderna.

Permite trabajar con voz, texto, pantalla, cámara, archivos locales, modelos de IA locales mediante Ollama y APIs externas como OpenRouter, OpenAI y ElevenLabs. Su objetivo es convertir una instrucción simple en resultados reales: documentos Word, libros Excel, presentaciones PowerPoint, páginas HTML, juegos, dashboards, imágenes, análisis de archivos, respuestas visuales y automatizaciones locales.

ARKEA AI está pensado como un asistente tipo agente para Windows: puede crear proyectos en carpetas locales, usar memoria, manejar skills, conectarse mediante MCP, generar vistas previas en vivo y trabajar con modelos locales o modelos en la nube según la tarea.

## Características principales

* Agente IA de escritorio para Windows.
* Interfaz Jade Glass / Aero Glass moderna.
* Chat por texto y voz.
* Respuesta por voz con voces del navegador y ElevenLabs.
* Visión por cámara, pantalla o imágenes subidas.
* Soporte para Ollama y modelos locales.
* Integración con OpenRouter como distribuidor de modelos.
* Integración con OpenAI compatible API.
* Creación de Word, Excel, PowerPoint, HTML, SVG, código e imágenes.
* Vista previa visual en vivo mientras crea.
* Memoria local y trabajo por carpetas.
* Sistema de skills en Markdown.
* MCP Hub para conectar herramientas externas.
* Preparado para automatización local tipo agente.
* Código abierto para revisión, mejora y colaboración.

## Autor

by: **Arkeai AI Roberto Manuel Jara Peche**



# ARKEA AI — Guía para ejecutar desde GitHub

**by: Arkeai AI Roberto Manuel Jara Peche**  
Proyecto: **ARKEA AI**

Este README es para el paquete de GitHub:

```txt
ARKEA_AI_REPOSITORIO_GITHUB_OPEN_SOURCE.zip
```

Sirve para subir el código fuente a GitHub, ejecutar el proyecto y generar el instalador `.exe`.

---

## 1. Qué ZIP usar

Para GitHub usa:

```txt
ARKEA_AI_REPOSITORIO_GITHUB_OPEN_SOURCE.zip
```

No uses este ZIP si solo quieres entregar la app a usuarios finales.  
Para usuarios finales se comparte el instalador `.exe` ya generado.

---

## 2. Estructura esperada

Al extraer el ZIP, la carpeta debe tener algo parecido a esto:

```txt
ARKEA_AI_REPOSITORIO_GITHUB/
│
├── arkea_ai_desktop_odysseus_overlay/
│   ├── backend/
│   ├── frontend/
│   ├── desktop/
│   ├── config/
│   ├── data/
│   └── requirements.txt
│
├── build_windows_installer.ps1
├── CREAR_EXE_ARKEA_AI.cmd
├── README.md
├── LICENSE
├── NOTICE
├── AUTHORS.md
├── .gitignore
└── .env.example
```

---

## 3. Comando principal para ejecutar desde GitHub/local

Después de clonar o descargar el repositorio, entra a la carpeta raíz y ejecuta:

```cmd
CREAR_EXE_ARKEA_AI.cmd
```

Ese comando crea el instalador `.exe` de ARKEA AI.

También puedes ejecutar el script técnico:

```cmd
powershell -ExecutionPolicy Bypass -File build_windows_installer.ps1
```

Pero lo recomendable es usar:

```cmd
CREAR_EXE_ARKEA_AI.cmd
```

---

## 4. Ejecutar desde CMD

Ejemplo si tu repositorio está en `C:\final`:

```cmd
cd /d C:\final\ARKEA_AI_REPOSITORIO_GITHUB
CREAR_EXE_ARKEA_AI.cmd
```

Ejemplo si está en Descargas:

```cmd
cd /d "%USERPROFILE%\Downloads\ARKEA_AI_REPOSITORIO_GITHUB"
CREAR_EXE_ARKEA_AI.cmd
```

---

## 5. Dónde aparece el instalador

Cuando termine, revisa la carpeta:

```txt
release
```

Ahí debe aparecer un archivo `.exe`, por ejemplo:

```txt
ARKEA-AI-Setup.exe
Instalador_ARKEA_AI.exe
ARKEA-AI-Setup-FINAL.exe
```

Ese `.exe` es el instalador final.

No compartas archivos que digan:

```txt
__uninstaller-nsis-arkea-ai.exe
```

Ese archivo es para desinstalar, no para instalar.

---

## 6. Cómo subir el código a GitHub

### Opción A: GitHub Desktop

1. Abre GitHub Desktop.
2. Clic en **File > Add local repository**.
3. Selecciona la carpeta del proyecto.
4. Si no es repositorio todavía, elige **Create a repository**.
5. Nombre recomendado:

```txt
arkea-ai
```

6. Clic en **Publish repository**.
7. Marca público si quieres que otros revisen el código.

---

### Opción B: CMD

Dentro de la carpeta del proyecto ejecuta:

```cmd
git init
git branch -M main
git add .
git commit -m "Publicar ARKEA AI open source"
git remote add origin https://github.com/TU_USUARIO/arkea-ai.git
git push -u origin main
```

Cambia `TU_USUARIO` por tu usuario real de GitHub.

---

## 7. Generar EXE desde GitHub Actions

Si el repositorio tiene este archivo:

```txt
.github/workflows/build-windows.yml
```

GitHub puede compilar el instalador automáticamente.

Pasos:

1. Entra a tu repositorio en GitHub.
2. Abre la pestaña **Actions**.
3. Elige **Build Windows Installer**.
4. Clic en **Run workflow**.
5. Espera a que termine.
6. Descarga el artefacto del workflow.
7. Dentro estará el instalador `.exe`.

---

## 8. Requisitos si compilas en tu PC

Verifica en CMD:

```cmd
git --version
node --version
npm --version
python --version
```

Si esos comandos muestran versión, puedes compilar.

---

## 9. Variables de entorno

No subas claves reales a GitHub.

Usa:

```txt
.env.example
```

Para tus claves personales crea localmente:

```txt
.env
```

Ejemplo:

```env
OPENROUTER_API_KEY=tu_clave_aqui
OPENAI_API_KEY=tu_clave_aqui
ELEVENLABS_API_KEY=tu_clave_aqui
```

El archivo `.env` debe estar en `.gitignore`.

---

## 10. Autoría y licencia

Mantén estos archivos:

```txt
LICENSE
NOTICE
AUTHORS.md
```

Autoría:

```txt
by: Arkeai AI Roberto Manuel Jara Peche
```

---

## 11. Resumen rápido

Para subir a GitHub:

```cmd
git init
git branch -M main
git add .
git commit -m "Publicar ARKEA AI open source"
git remote add origin https://github.com/TU_USUARIO/arkea-ai.git
git push -u origin main
```

Para crear el instalador:

```cmd
CREAR_EXE_ARKEA_AI.cmd
```

Para encontrar el instalador:

```txt
release
```

Para compilar desde GitHub:

```txt
GitHub > Actions > Build Windows Installer > Run workflow
```
