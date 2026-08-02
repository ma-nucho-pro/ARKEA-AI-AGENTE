# Política y modelo de seguridad

## Versiones cubiertas

Esta política cubre ARKEA AI OmniAgent 0.1, OmniRoute 3.8.49 y Ollama
0.32.5 fijados por esta distribución. Una sustitución de versión requiere una
nueva revisión de código, hashes y pruebas.

## Fronteras de confianza

ARKEA procesa archivos del usuario, resultados de modelos, APIs remotas,
servidores MCP y procesos locales. Todo ello se considera entrada no confiable.
La aplicación no debe exponerse a una red:

- el backend escucha en `127.0.0.1` y usa un token aleatorio por proceso;
- el renderer de Electron tiene `contextIsolation`, sin Node.js;
- el IPC solo acepta el frame superior y el origen exacto del backend;
- OmniRoute escucha en `127.0.0.1:20128`, exige Bearer API key y se valida por
  versión y por `/v1/models` autenticado;
- ARKEA rechaza URLs OmniRoute que no sean HTTP de loopback en el puerto 20128.

## Secretos

La clave interna, JWT, contraseña inicial y clave de cifrado de OmniRoute se
almacenan con `safeStorage`, respaldado por DPAPI en Windows. Si DPAPI no está
disponible, ARKEA se niega a guardar o iniciar esos secretos. Una instalación
anterior con `runtime-secrets.json` se migra a
`runtime-secrets.bin` y se elimina el archivo legado.

La contraseña inicial del panel solo se muestra mediante IPC autenticado y un
diálogo nativo. Debe cambiarse después del primer acceso. La clave interna API
no se presenta en la interfaz. Las claves de proveedores permanecen bajo la
gestión de OmniRoute o en el almacén de ARKEA elegido por el usuario.

No publiques `.env`, bases de datos, logs, capturas con claves ni el directorio
de datos de la aplicación.

## Cadena de suministro

- OmniRoute y Ollama tienen versión, URL HTTPS, tamaño y SHA-256 fijados.
- OmniRoute se descarga desde su Release oficial mediante el navegador. Si el
  archivo exacto está en `Descargas`, ARKEA valida tamaño y SHA-256 antes de
  abrirlo; la instalación siempre usa el asistente visible del proveedor.
- Solo se inicia un ejecutable OmniRoute encontrado en ubicaciones de instalación
  conocidas y con versión 3.8.49 o posterior compatible.
- Python y npm se fijan en lockfiles.
- `SBOM-ARKEA-OMNIAGENT.json` inventaría ambos lockfiles y los sidecars.
- `SHA256SUMS.txt` permite verificar cada artefacto final.

Esta entrega no está firmada con Authenticode porque no se proporcionó un
certificado. Los hashes reducen el riesgo de sustitución, pero no equivalen a
una firma de editor. El builder admite firma cuando se configuran `CSC_LINK` y
`CSC_KEY_PASSWORD`.

## Red y SSRF

Las solicitudes salientes se validan, limitan en tamaño y bloquean destinos
locales o privados salvo integraciones locales explícitas. Las excepciones
locales se restringen a proveedores conocidos y endpoints configurados para
ese modo. El modo API directa excluye loopback y proveedores locales.

No habilites acceso LAN ni URLs privadas de proveedores sin evaluar la nueva
frontera de confianza.

## Herramientas MCP

Los procesos MCP se ejecutan con `shell=False`, entorno reducido, comandos
permitidos, entrada acotada, timeout, stdout/stderr acotados y terminación del
árbol de procesos. Se aplican permisos de admisión por operación, incluido
`execute` para toda tool. No son un sandbox del sistema operativo: un proceso
autorizado puede ignorar sus declaraciones. La confirmación es obligatoria por
defecto. Solo los servidores que el usuario marque expresamente como autónomos
se ofrecen al modelo, y siguen sujetos a sus permisos.

Los nombres y argumentos de una herramienta pueden ser maliciosos. Revisa el
servidor, concede el mínimo permiso y no desactives confirmación para código
que no controles.

## Skills, modelos y contenido generado

Las instrucciones de una skill se incorporan a todas las llamadas respaldadas
por modelos, pero sus permisos son metadatos y no controles de acceso. Los
modelos pueden equivocarse o intentar llamadas indebidas; los controles MCP,
filesystem, IPC y red son la frontera efectiva.

No ejecutes automáticamente código generado ni abras ejecutables desde el
workspace. La función de apertura bloquea extensiones ejecutables conocidas.

## Datos y aislamiento

Esta edición usa `Documentos\ARKEA AI OmniAgent` y su propio directorio
`userData`; no comparte workspace ni vault con la edición anterior. Desinstalar
la aplicación no sustituye una copia de seguridad.

## Reportar una vulnerabilidad

No abras un Issue público con secretos, datos personales o una prueba que
afecte a terceros. Envía:

- versión y hash del artefacto;
- pasos mínimos de reproducción;
- impacto esperado;
- logs redactados;
- propuesta de mitigación, si existe.

Contacto:

- robertmanuchojarapeche@gmail.com
- betomanuchobullicio@gmail.com

Elimina tokens, rutas personales, bases de datos, correos y archivos privados
antes de adjuntar cualquier material.
