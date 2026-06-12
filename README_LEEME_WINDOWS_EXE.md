# Arkea AI V7

Esta versión corrige el micrófono para no depender de SpeechRecognition de Chromium. El botón Hablar graba WAV y manda el audio al backend: usa API STT configurada o faster-whisper local.

## Construir

```cmd
cd C:\ARKEA_BUILD_V7\ARKEA_AI_Desktop_Windows_EXE_Builder_V7_VOICE_CAMERA_SCREEN_AUTOMATION
powershell -ExecutionPolicy Bypass -File build_windows_installer.ps1
```

## Funciones nuevas

- Sin archivo: al hacer clic permite elegir carpeta de trabajo y crea nuevo chat en esa carpeta.
- Cámara: captura la cámara y la analiza con API de visión u Ollama vision.
- Pantalla: captura pantalla y la analiza con API de visión u Ollama vision.
- Modelos: recomienda modelos según RAM/espacio, instala Ollama y descarga modelos por ID.
- APIS: separa chat, visión, imagen, video, voz TTS, voz STT, traducción, embedding, automation y custom.
- MCP/Automatización: modo seguro con permiso y confirmación.

