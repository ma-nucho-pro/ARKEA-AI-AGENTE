ARKEA AI Desktop - Builder V5 BRAND + API

Corrige:
- Backend congelado con PyInstaller: ya no consulta SQLite antes de crear tablas.
- Rutas internas en modo EXE.
- Preview de proyectos aunque la carpeta esté en Documentos.
- Logs visibles si el backend no inicia.

Agrega:
- Logo e icono ARKEA en interfaz e instalador.
- Panel Modelos: detecta Ollama, instala Ollama, recomienda modelos según RAM/espacio y descarga por ID.
- Panel Ajustes/API: permite configurar endpoint, API key y model ID para chat e imagen.
- API de imagen genérica: si pones un endpoint compatible con generación de imágenes, ARKEA intentará usarlo; si no, crea placeholder SVG.

Uso:
1. Extrae esta carpeta en C:\ARKEA_BUILD_V5
2. Abre CMD
3. cd C:\ARKEA_BUILD_V5\ARKEA_AI_Desktop_Windows_EXE_Builder_V5_BRAND_API
4. powershell -ExecutionPolicy Bypass -File build_windows_installer.ps1
5. Instala release\ARKEA-AI-Desktop-Setup-0.5.0.exe

Si falla, copia el texto completo desde donde dice ERROR y revisa logs en:
%APPDATA%\ARKEA AI Desktop\logs\backend-err.log
