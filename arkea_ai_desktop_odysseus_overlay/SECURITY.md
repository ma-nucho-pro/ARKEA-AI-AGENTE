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

## Controles implementados

- El backend escucha únicamente en loopback y exige un token aleatorio por ejecución para `/api/*`.
- Las vistas HTML generadas se ejecutan en un `iframe` sandbox sin origen compartido ni acceso al puente Electron.
- Los IPC validan que el remitente sea el frame principal local; navegación, ventanas y protocolos externos están limitados.
- `arkea.db` y las cargas privadas no se publican como contenido estático.
- Las claves se cifran con Windows DPAPI y se ocultan en las respuestas de ajustes.
- Las cargas y respuestas remotas tienen límites de tamaño.
- Las URL configurables bloquean redes privadas, loopback no autorizado y redirecciones SSRF.

## Verificación

Ejecutar desde la raíz del proyecto:

```powershell
python -m unittest discover -s tests -v
node --check frontend/app.js
node --check desktop/main.js
npm.cmd audit --prefix desktop
```
