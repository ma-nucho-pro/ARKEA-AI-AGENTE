# Seguridad de ARKEA AI Desktop

ARKEA tendrá control local, por eso debe operar con permisos limitados.

Reglas recomendadas:

- Trabajar solo dentro del workspace configurado.
- Confirmar antes de ejecutar comandos de terminal.
- Confirmar antes de usar MCPs con correo, calendario, archivos externos o apps de escritorio.
- No guardar API keys en el frontend.
- Guardar API keys en almacén seguro del sistema o `.env` local no subido a Git.
- Bloquear conectores de contenido no autorizado como Sci-Hub.
- Registrar todo en `tool_events`.
