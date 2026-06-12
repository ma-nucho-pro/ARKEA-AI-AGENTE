Arkea AI V8 - Fix funciones

Correcciones principales:
- Botones de Nuevo chat, Cambiar carpeta, Abrir carpeta, Preview, Skills, APIS, Modelos y Descargar ahora usan eventos robustos.
- Nuevo chat permite seleccionar carpeta y esa carpeta queda como workspace del chat.
- El botón "Sin archivo" también permite seleccionar carpeta y crear chat.
- El botón Descargar ya no manda a Descargas: abre la carpeta del chat/proyecto.
- El dictado ya no usa el motor SpeechRecognition de Chromium. Graba WAV y transcribe por backend.
- Whisper local usa vad_filter=False para evitar el error silero_vad_v6.onnx.
- Botón Descargar/activar Whisper tiny intenta preparar el modelo tiny en el cache del usuario.
- Captura de pantalla usa desktopCapturer de Electron si getDisplayMedia no está disponible.
- Cámara conserva getUserMedia y analiza imagen con API de visión u Ollama vision.
- Ollama: si falla la descarga automática, abre/entrega link oficial. También recomienda modelos por RAM/disco.
- Nombre por defecto del usuario: Manu.

Compilar:
1) Extrae en C:\ARKEA_BUILD_V8
2) CMD:
   cd C:\ARKEA_BUILD_V8\ARKEA_AI_Desktop_Windows_EXE_Builder_V8_FINAL_FIX_FUNCTIONS
   powershell -ExecutionPolicy Bypass -File build_windows_installer.ps1
3) El instalador saldrá en release\ARKEA-AI-Desktop-Setup-0.8.0.exe

Pruebas después de instalar:
- Clic en "Sin archivo" -> elegir carpeta.
- Nuevo chat -> elegir carpeta.
- Hablar -> detener y enviar -> debe transcribir en el cuadro y enviar si Autoenviar voz está activo.
- Cámara -> mostrar un objeto.
- Pantalla -> capturar primera pantalla/ventana disponible.
- Ajustes > Skills -> crear skill o subir .md.
- Ajustes > Modelos -> Instalar Ollama / Descargar recomendados.
- Ajustes > APIS -> guardar API por tipo.
