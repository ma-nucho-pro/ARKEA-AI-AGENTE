# ARKEA AI OmniAgent 0.1

Código fuente abierto de ARKEA AI OmniAgent para Windows, distribuido bajo
`AGPL-3.0-or-later`.

La aplicación integra agentes, skills y herramientas MCP con distintos motores
de IA: Ollama local, OmniRoute para proveedores gratuitos o externos y APIs
compatibles configuradas por el usuario.

## Descargar para usar

Los usuarios finales no necesitan clonar ni compilar el proyecto. Deben abrir
la sección **Releases** de GitHub:

**[Descargar la última versión de ARKEA AI OmniAgent](https://github.com/ma-nucho-pro/ARKEA-AI-AGENTE/releases/latest)**

Después deben descargar uno de estos archivos:

- `0_1-COMIENZA-POR-AQUI-ARKEA-AI-OmniAgent-Setup-0.1.0.exe`: instalador
  tradicional de Windows con asistente.
- `0_1-ARKEA-AI-OmniAgent-Windows-x64-portable.zip`: versión portable.

Los binarios se publican como archivos de una Release porque superan el límite
de tamaño de un archivo normal del repositorio. El código fuente permanece
completo y revisable aquí.

Consulta [INSTALACION.md](INSTALACION.md) para los pasos de usuario y
desarrollador. Para publicar este repositorio por primera vez sigue
[GUIA_PUBLICAR_GITHUB.md](GUIA_PUBLICAR_GITHUB.md).

## Documentación del proyecto

Lee primero [README_0_1_COMIENZA_POR_AQUI.md](README_0_1_COMIENZA_POR_AQUI.md).
Incluye arquitectura, requisitos, instalación, seguridad y comandos para Codex,
Claude Code, OpenClaw y compilación manual.

## Construcción para Windows

Con doble clic:

```text
0_1_CREAR_EXE_OMNIAGENT.cmd
```

Desde PowerShell:

```powershell
.\build_windows_installer.ps1
```

El constructor obtiene la revisión exacta indicada en `SOURCE-REVISION.txt`,
aplica `arkea_ai_desktop_odysseus_overlay`, ejecuta verificaciones y genera los
artefactos dentro de `release/`.

Para publicar esos artefactos desde una consola autenticada con GitHub CLI:

```powershell
.\PUBLICAR_RELEASE_GITHUB.cmd v0.1.0
```

Subir el código no publica automáticamente los binarios grandes. Son dos pasos
separados y deliberados: primero `SUBIR_CODIGO_GITHUB.cmd` y después
`PUBLICAR_RELEASE_GITHUB.cmd`. Las pruebas de contribuciones sí se ejecutan
automáticamente mediante `.github/workflows/ci.yml`.

## Contribuir

Lee [CONTRIBUTING.md](CONTRIBUTING.md). Los cambios de ARKEA se realizan
principalmente en `arkea_ai_desktop_odysseus_overlay/`; `source-tree/` conserva
el árbol correspondiente exacto de la versión publicada.

## Seguridad y contribuciones

- No subas archivos `.env`, claves, bases de datos ni secretos de ejecución.
- Revisa [SECURITY.md](SECURITY.md) antes de habilitar MCPs o proveedores.
- Conserva `LICENSE`, `NOTICE`, `SOURCE-OFFER.md` y las licencias de terceros al
  redistribuir binarios.

OmniRoute y las cuotas gratuitas dependen de proveedores externos. Una
instalación nueva requiere conectar al menos un proveedor con capacidad para
obtener respuestas remotas; Ollama ofrece el modo local.
