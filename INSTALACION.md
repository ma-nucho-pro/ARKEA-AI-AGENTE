# Instalación y construcción

## Usuarios de Windows

1. Abre [Releases de ARKEA AI](https://github.com/ma-nucho-pro/ARKEA-AI-AGENTE/releases/latest).
2. Descarga
   `0_1-COMIENZA-POR-AQUI-ARKEA-AI-OmniAgent-Setup-0.1.0.exe`.
3. Ejecuta el archivo y sigue el asistente de Windows.
4. Abre ARKEA AI OmniAgent y elige IA local, IA gratuita o una API propia.

El instalador incluye la aplicación, su backend y el instalador verificado de
Ollama. El botón **Instalar IA gratis** obtiene la versión fijada de OmniRoute y
verifica su tamaño y SHA-256 antes de ejecutarla.

La entrega no tiene firma Authenticode. Windows puede mostrar SmartScreen; los
hashes oficiales se adjuntan en `SHA256SUMS.txt` dentro de cada Release.

## Versión portable

Descarga `0_1-ARKEA-AI-OmniAgent-Windows-x64-portable.zip`, extráelo por
completo y abre `ARKEA AI OmniAgent.exe`. No ejecutes el programa desde dentro
del ZIP.

## Compilar con doble clic

Instala Git, Python 3.11 y Node.js 22. Después clona o descarga el repositorio y
haz doble clic en:

```text
0_1_CREAR_EXE_OMNIAGENT.cmd
```

Los resultados se generan en `release/`.

## Compilar desde PowerShell

```powershell
git clone https://github.com/ma-nucho-pro/ARKEA-AI-AGENTE.git
cd ARKEA-AI-AGENTE
.\build_windows_installer.ps1
```

## Desarrollo local

```powershell
cd arkea_ai_desktop_odysseus_overlay
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
$env:ARKEA_DEV_NO_AUTH = "1"
.\.venv\Scripts\python.exe start_arkea.py
```

`ARKEA_DEV_NO_AUTH=1` solo se admite en desarrollo, fuera del ejecutable
empaquetado y enlazado a loopback.

## IA gratuita

OmniRoute facilita el uso de múltiples proveedores y sus cuotas, pero no crea
cuotas ilimitadas. Para obtener respuestas remotas hay que conectar al menos un
proveedor con capacidad disponible. Ollama continúa disponible como alternativa
local y privada.
