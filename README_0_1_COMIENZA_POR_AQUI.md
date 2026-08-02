# ARKEA AI OmniAgent 0.1

Esta es una edición nueva e independiente. No modifica la instalación ni el
repositorio de la edición anterior de ARKEA.

Integra:

- ARKEA como interfaz y agente de escritorio.
- OmniRoute 3.8.49 o posterior compatible como gateway local multi-IA.
- Ollama 0.32.5 como motor local opcional.
- APIs directas compatibles configuradas por el usuario.
- Skills para todas las llamadas respaldadas por modelos.
- Herramientas integradas y MCP con permisos, límites y confirmación.

## Instalación para usuarios

1. Verifica `SHA256SUMS.txt`.
2. Ejecuta
   `0_1-COMIENZA-POR-AQUI-ARKEA-AI-OmniAgent-Setup-0.1.0.exe`.
3. Abre **ARKEA AI OmniAgent**.
4. En la bienvenida puedes abrir el instalador oficial de OmniRoute o preparar
   Ollama.
5. Para OmniRoute, completa su asistente visible y después pulsa
   **Ajustes → IA universal → Detectar e iniciar**.

La aplicación instalada incluye su backend; no requiere Python ni Node.js.
ARKEA abre la descarga oficial fijada de OmniRoute; no intenta descargarlo ni
instalarlo mediante CMD. Si el instalador exacto ya está en `Descargas`, ARKEA
comprueba tamaño y SHA-256 antes de abrirlo. OmniRoute se instala como programa
independiente mediante su asistente visible. Ollama se incluye como instalador
oficial también fijado y verificado.

Los ejecutables de esta entrega no llevan firma Authenticode porque el proyecto
no dispone de certificado de firma. Windows puede mostrar SmartScreen. No
ignores ese aviso sin comparar antes el SHA-256 publicado.

El código fuente correspondiente exacto se incluye en
`ARKEA-AI-OmniAgent-0.1.0-source.zip` y también dentro de la aplicación en
`resources/legal/`. Consulta `SOURCE-OFFER.md`; el archivo de fuentes también
está cubierto por `SHA256SUMS.txt`.

## Modos de IA

- **Automático:** intenta OmniRoute y conexiones configuradas; Ollama es el
  último recurso explícito.
- **Gratis:** usa solamente OmniRoute. No cambia a API directa, Ollama ni a una
  imagen local de sustitución.
- **Local:** usa solamente Ollama o generadores locales configurados.
- **API directa:** usa solamente APIs remotas guardadas por el usuario. Excluye
  OmniRoute, Ollama y endpoints de loopback.

“Gratis” significa que ARKEA no cobra por el enrutamiento. Una respuesta real
depende de que el usuario conecte en OmniRoute un proveedor, cuenta, OAuth o
credencial que ofrezca capacidad disponible. ARKEA no promete que terceros
mantengan cuotas o modelos gratuitos.

## Seguridad local

- ARKEA y OmniRoute escuchan en loopback.
- OmniRoute 3.8.49 o posterior compatible se inicia con
  `REQUIRE_API_KEY=true`.
- La clave interna y los secretos de OmniRoute se cifran mediante
  `safeStorage`/DPAPI de Windows; no se guardan en JSON de texto plano.
- ARKEA detecta la instalación oficial en ubicaciones conocidas de Windows y
  comprueba que su versión sea 3.8.49 o posterior antes de iniciarla.
- No reutiliza un proceso ajeno en el puerto 20128. El estado de salud comprueba
  identidad, versión compatible y consulta autenticada de `/v1/models`.
- El backend de ARKEA exige un token aleatorio por proceso y no escucha en LAN.
- La carpeta de trabajo es
  `Documentos\ARKEA AI OmniAgent\Projects`; el vault es independiente de la
  edición anterior.

Al pulsar **Abrir OmniRoute**, ARKEA muestra la contraseña inicial del panel en
un diálogo local confiable. Debes cambiarla en el panel después de la primera
configuración. La clave interna de API no se revela.

## Skills y MCP

La skill activa se añade a las llamadas de texto, código, documentos, visión,
búsqueda e imágenes. Las acciones deterministas de interfaz o filesystem siguen
la orden concreta del usuario; los permisos declarados en una skill son
metadatos de capacidad, no una frontera de seguridad.

MCP sí aplica una frontera de ejecución:

- comandos sin `shell`, dentro de una lista permitida;
- argumentos y entrada limitados;
- stdout y stderr leídos con memoria acotada;
- timeout y terminación del árbol de procesos;
- permisos `read`, `write`, `network`, `execute`, `browser` y `filesystem`;
- confirmación manual por defecto;
- bucle autónomo modelo→MCP únicamente para servidores que el usuario haya
  marcado sin confirmación.

Una herramienta MCP no se presenta al modelo como autónoma mientras requiera
confirmación. Los resultados se obtienen de llamadas MCP reales y se devuelven
al modelo para producir la respuesta final.

Todo servidor necesita `execute`, porque MCP inicia código externo. Los demás
permisos controlan la admisión de llamadas según nombre y argumentos; no son un
sandbox del sistema operativo. Un servidor autorizado podría comportarse de
forma distinta a lo que declara, por lo que la confirmación debe seguir activa
salvo para código de confianza.

## Configurar otros agentes

OmniRoute exige autenticación. Para usarlo desde otro agente, abre su panel,
conecta tus proveedores y crea una clave propia para ese cliente. No uses ni
intentes extraer la clave interna administrada por ARKEA.

### Claude Code

Con la CLI opcional de OmniRoute:

```powershell
omniroute setup-claude
omniroute launch
```

Configuración manual para la sesión actual:

```powershell
$env:ANTHROPIC_BASE_URL="http://127.0.0.1:20128"
$env:ANTHROPIC_AUTH_TOKEN=$env:MI_CLAVE_OMNIROUTE
claude
```

Define `MI_CLAVE_OMNIROUTE` de forma segura antes de ejecutar el comando.

### Codex

Con la CLI opcional:

```powershell
omniroute setup-codex
omniroute launch-codex
```

En una configuración manual usa:

```text
base_url = http://127.0.0.1:20128/v1
model = auto
api_key = variable de entorno creada por el usuario
```

### OpenClaw

No pases la clave como texto literal en el historial del shell. Primero
consulta la documentación de la versión instalada de OpenClaw y usa su entrada
interactiva o secret store para registrar:

```text
base URL: http://127.0.0.1:20128/v1
model: auto
compatibilidad: OpenAI
API key: clave de cliente creada en el panel de OmniRoute
```

Los argumentos exactos de OpenClaw pueden cambiar entre versiones; evita
`--secret-input-mode plaintext`.

## Compilar

Requisitos del equipo de compilación:

- Windows 10/11 x64.
- Python 3.11.
- Node.js 24 LTS.
- Git para Windows (obligatorio; se verifica el commit Odysseus fijado).
- Espacio libre suficiente para el backend, Electron y Ollama.

Ejecuta:

```cmd
0_1_CREAR_EXE_OMNIAGENT.cmd
```

El constructor crea el backend congelado, comprueba su salud, usa los lockfiles,
verifica Ollama, construye NSIS y portable, y genera `SHA256SUMS.txt`.
Para firmar, configura un certificado válido mediante `CSC_LINK` y
`CSC_KEY_PASSWORD`.

## Verificación de desarrollo

Desde `arkea_ai_desktop_odysseus_overlay`:

```powershell
python -m pytest -q tests
node --check desktop/main.js
node --check desktop/preload.js
node --check frontend/app.js
cd desktop
npm audit
```

El inventario completo está en `SBOM-ARKEA-OMNIAGENT.json`. Consulta también
`SECURITY.md`, `LICENCIAS-TERCEROS.txt` y
`VALIDACION_OMNIROUTE_REAL.json`.

## Límites

Ninguna revisión garantiza ausencia absoluta de vulnerabilidades. Mantén
copias de seguridad, protege las cuentas conectadas a los proveedores, revisa
los permisos MCP y actualiza las versiones fijadas solamente después de volver
a auditar y probar la distribución.

Fuentes:

- https://github.com/diegosouzapw/OmniRoute
- https://github.com/diegosouzapw/OmniRoute/wiki/Environment
- https://github.com/diegosouzapw/OmniRoute/wiki/API-Reference
- https://github.com/ollama/ollama
