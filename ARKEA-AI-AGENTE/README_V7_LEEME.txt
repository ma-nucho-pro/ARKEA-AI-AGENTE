ARKEA AI Desktop V7

Correcciones principales:
- El botón Hablar ya no depende de SpeechRecognition/Chromium. Graba audio WAV y lo envía al backend para STT local/API.
- Agrega botón Cámara para capturar imagen y analizarla con API de visión u Ollama vision.
- Agrega botón Pantalla para capturar pantalla y analizarla con API de visión u Ollama vision.
- El botón Sin archivo abre selector de carpeta de trabajo.
- Modelos locales: recomienda por RAM/espacio y permite instalar Ollama + descargar modelo por ID.
- Botón para instalar modelos recomendados para la PC.
- APIS separadas por tipo: chat, vision, image, video, voice_tts, voice_stt, translation, embedding, automation, custom.
- Automatización del ordenador/navegador queda en modo seguro: requiere permisos y confirmación.

Nota: Para STT completamente offline se incluye soporte para faster-whisper si se instala/compila correctamente. Si no se dispone del modelo, usa una API STT configurada en APIS.
