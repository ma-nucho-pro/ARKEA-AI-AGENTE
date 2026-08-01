# Guía exacta para sustituir el repositorio y publicar la descarga

Repositorio de destino:

<https://github.com/ma-nucho-pro/ARKEA-AI-AGENTE>

Carpeta local que debes usar:

```text
C:\arkea\0_1-GITHUB-CODIGO-FUENTE-ARKEA-AI-OMNIAGENT
```

No subas la carpeta antigua ni `0_1 COMIENZA POR AQUI - ARKEA AI OMNIAGENT`.

## Qué ocurrirá

Son dos publicaciones diferentes:

1. **Código:** reemplaza todos los archivos visibles de la rama `main` por el
   nuevo proyecto abierto. El historial anterior se conserva.
2. **Release:** crea la página de descarga y adjunta el instalador, portable,
   código fuente y hashes.

Subir el código por sí solo no sube el instalador de 1,8 GB. Por eso existen
dos botones separados.

## Paso 1 — Instalar GitHub CLI una sola vez

1. Abre <https://cli.github.com/>.
2. En **Windows**, pulsa **Download MSI**.
3. Ejecuta el MSI y termina la instalación.
4. Cierra todas las ventanas de PowerShell o CMD y abre una nueva.

Comprueba:

```powershell
gh --version
```

## Paso 2 — Iniciar sesión una sola vez

En PowerShell ejecuta:

```powershell
gh auth login
```

Selecciona:

1. `GitHub.com`.
2. `HTTPS`.
3. Confirma que quieres autenticar Git.
4. `Login with a web browser`.
5. Copia el código mostrado, abre el navegador y autoriza tu cuenta
   `ma-nucho-pro`.

Al terminar verifica:

```powershell
gh auth status
```

## Paso 3 — Reemplazar el código anterior

Abre en el Explorador de Windows:

```text
C:\arkea\0_1-GITHUB-CODIGO-FUENTE-ARKEA-AI-OMNIAGENT
```

Haz doble clic en:

```text
SUBIR_CODIGO_GITHUB.cmd
```

El programa te pedirá dos confirmaciones. Pulsa `S` en ambas. El script:

- clona `ma-nucho-pro/ARKEA-AI-AGENTE` en una carpeta temporal;
- elimina del nuevo commit los archivos antiguos;
- copia todo el proyecto abierto nuevo;
- conserva el historial de Git;
- no sube `release/`, secretos, bases de datos ni dependencias;
- crea el commit y lo envía a `main`.

No elimina issues, estrellas ni Releases anteriores. Solo sustituye el contenido
visible actual del código.

Comprueba el resultado en:

<https://github.com/ma-nucho-pro/ARKEA-AI-AGENTE>

## Paso 4 — Publicar el instalador y portable

En la misma carpeta haz doble clic en:

```text
PUBLICAR_RELEASE_GITHUB.cmd
```

No necesitas compilar ahora: la carpeta local `release/` ya contiene los
artefactos aprobados. El proceso puede tardar bastante porque subirá casi 3,7 GB.

El script creará o actualizará `v0.1.0` y subirá:

- `0_1-COMIENZA-POR-AQUI-ARKEA-AI-OmniAgent-Setup-0.1.0.exe`;
- `0_1-ARKEA-AI-OmniAgent-Windows-x64-portable.zip`;
- `ARKEA-AI-OmniAgent-0.1.0-source.zip`;
- `SHA256SUMS.txt`.

Comprueba la descarga en:

<https://github.com/ma-nucho-pro/ARKEA-AI-AGENTE/releases/latest>

El README ya contiene ese enlace, por lo que los visitantes podrán pulsar
**Descargar la última versión de ARKEA AI OmniAgent**.

## Paso 5 — Futuras versiones

Solo cuando cambies el producto y quieras generar instaladores nuevos:

1. Haz doble clic en `0_1_CREAR_EXE_OMNIAGENT.cmd`.
2. Prueba el resultado creado dentro de `release/`.
3. Publica con una versión nueva desde PowerShell, por ejemplo:

```powershell
.\PUBLICAR_RELEASE_GITHUB.cmd v0.1.1
```

Actualiza también los nombres/versiones de los archivos cuando cambie la versión
del producto.
