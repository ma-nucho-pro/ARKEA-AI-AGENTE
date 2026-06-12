$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Arkea AI - Builder Windows .EXE V9 AERO LIVE SCREEN" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Work = Join-Path $Root "_work"
$Release = Join-Path $Root "release"
$Overlay = Join-Path $Root "arkea_ai_desktop_odysseus_overlay"
$Ody = Join-Path $Work "odysseus"

function Need-Cmd($cmd, $msg) {
  $found = Get-Command $cmd -ErrorAction SilentlyContinue
  if (-not $found) {
    Write-Host "FALTA: $cmd" -ForegroundColor Red
    Write-Host $msg -ForegroundColor Yellow
    exit 1
  }
}

function Write-Utf8NoBom($Path, $Content) {
  $enc = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Content, $enc)
}

function Show-Log-Tail($Path, $N=160) {
  if (Test-Path $Path) {
    Write-Host "----- $Path -----" -ForegroundColor Yellow
    Get-Content $Path -Tail $N
  }
}

function Start-Backend-Test($ExePath, $Cwd, $Port, $LogDir) {
  New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
  $outLog = Join-Path $LogDir "backend-test-out.log"
  $errLog = Join-Path $LogDir "backend-test-err.log"
  if (Test-Path $outLog) { Remove-Item $outLog -Force }
  if (Test-Path $errLog) { Remove-Item $errLog -Force }

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $ExePath
  $psi.WorkingDirectory = $Cwd
  $psi.UseShellExecute = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.CreateNoWindow = $true
  $psi.EnvironmentVariables["PYTHONUTF8"] = "1"
  $psi.EnvironmentVariables["ARKEA_HOST"] = "127.0.0.1"
  $psi.EnvironmentVariables["ARKEA_PORT"] = [string]$Port
  $psi.EnvironmentVariables["ARKEA_DATA_DIR"] = (Join-Path $LogDir "Data")
  $psi.EnvironmentVariables["ARKEA_DB_PATH"] = (Join-Path $LogDir "Data\arkea.db")
  $psi.EnvironmentVariables["ARKEA_WORKSPACE"] = (Join-Path $LogDir "Projects")
  $psi.EnvironmentVariables["ARKEA_OBSIDIAN_VAULT"] = (Join-Path $LogDir "ObsidianVault")

  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  [void]$p.Start()

  Start-Sleep -Milliseconds 400
  for ($i=0; $i -lt 75; $i++) {
    Start-Sleep -Milliseconds 700
    if ($p.HasExited) { break }
    try {
      $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/health" -UseBasicParsing -TimeoutSec 2
      if ($r.StatusCode -eq 200) {
        if (-not $p.HasExited) { $p.Kill() | Out-Null }
        Write-Host "Backend compilado probado correctamente." -ForegroundColor Green
        return
      }
    } catch {}
  }

  try { $p.StandardOutput.ReadToEnd() | Out-File -Encoding utf8 $outLog } catch {}
  try { $p.StandardError.ReadToEnd() | Out-File -Encoding utf8 $errLog } catch {}
  if (-not $p.HasExited) { $p.Kill() | Out-Null }
  Start-Sleep -Milliseconds 500

  Write-Host "El backend compilado NO iniciÃ³. Logs:" -ForegroundColor Red
  Show-Log-Tail $outLog
  Show-Log-Tail $errLog
  throw "Backend compilado no pasÃ³ la prueba de /api/health"
}

Need-Cmd git "Instala Git para Windows: https://git-scm.com/download/win"
Need-Cmd python "Instala Python 3.11 o 3.12 y marca 'Add Python to PATH'."
Need-Cmd node "Instala Node.js LTS: https://nodejs.org/"
Need-Cmd npm.cmd "Node.js debe incluir npm. Este builder usa npm.cmd."

if (Test-Path $Work) { Remove-Item $Work -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Work | Out-Null
New-Item -ItemType Directory -Force -Path $Release | Out-Null

Write-Host "[1/9] Clonando Odysseus..." -ForegroundColor Green
git clone https://github.com/pewdiepie-archdaemon/odysseus.git $Ody

Write-Host "[2/9] Aplicando overlay ARKEA encima de Odysseus..." -ForegroundColor Green
python (Join-Path $Overlay "patch_into_odysseus.py") --odysseus $Ody

Write-Host "[3/9] Creando entorno Python..." -ForegroundColor Green
Set-Location $Ody
python -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel

if (Test-Path ".\ARKEA_requirements.txt") {
  & ".\.venv\Scripts\python.exe" -m pip install -r ".\ARKEA_requirements.txt"
} elseif (Test-Path ".\requirements.txt") {
  & ".\.venv\Scripts\python.exe" -m pip install -r ".\requirements.txt"
}
& ".\.venv\Scripts\python.exe" -m pip install pyinstaller

Write-Host "[4/9] Compilando backend Python como arkea-backend.exe..." -ForegroundColor Green
$PyInstallerArgs = @(
  "--clean", "--noconfirm", "--onedir", "--name", "arkea-backend",
  "--add-data", "backend;backend",
  "--add-data", "frontend;frontend",
  "--add-data", "data;data",
  "--add-data", "config;config",
  "--collect-submodules", "backend",
  "--collect-all", "fastapi",
  "--collect-all", "starlette",
  "--collect-all", "pydantic",
  "--collect-all", "uvicorn",
  "--collect-all", "anyio",
  "--collect-all", "requests",
  "--collect-all", "PIL",
  "--collect-all", "pptx",
  "--collect-all", "docx",
  "--collect-all", "openpyxl",
  "--collect-all", "markdown",
  "--collect-all", "bs4",
  "--collect-all", "faster_whisper",
  "--collect-all", "ctranslate2",
  "--collect-all", "tokenizers",
  "--collect-all", "huggingface_hub",
  "--collect-all", "onnxruntime",
  "--collect-all", "av",
  "--hidden-import", "backend.arkea_app",
  "--hidden-import", "uvicorn.logging",
  "--hidden-import", "uvicorn.loops.auto",
  "--hidden-import", "uvicorn.protocols.http.auto",
  "--hidden-import", "uvicorn.protocols.websockets.auto",
  "--hidden-import", "multipart",
  "--hidden-import", "psutil",
  "start_arkea.py"
)
& ".\.venv\Scripts\python.exe" -m PyInstaller @PyInstallerArgs

Write-Host "[5/9] Probando backend compilado antes de crear el instalador..." -ForegroundColor Green

# En tu PC puede existir exactamente esta ruta, pero en GitHub Actions el bundle de PyInstaller
# puede quedar en otra ruta dentro de dist. Por eso se busca de forma robusta.
$DistRoot = Join-Path $Ody "dist"
$ExpectedBackendDir = Join-Path $DistRoot "arkea-backend"
$ExpectedBackendExe = Join-Path $ExpectedBackendDir "arkea-backend.exe"
$CompiledExe = $ExpectedBackendExe

if (-not (Test-Path $CompiledExe)) {
  Write-Host "No se encontrÃ³ backend en ruta fija. Buscando arkea-backend.exe dentro de dist..." -ForegroundColor Yellow

  $BackendCandidate = $null
  if (Test-Path $DistRoot) {
    $BackendCandidate = Get-ChildItem -Path $DistRoot -Filter "arkea-backend.exe" -Recurse -ErrorAction SilentlyContinue |
      Select-Object -First 1
  }

  if ($BackendCandidate) {
    $CompiledExe = $BackendCandidate.FullName
    Write-Host "Backend encontrado en: $CompiledExe" -ForegroundColor Green
  }
}

if (-not (Test-Path $CompiledExe)) {
  Write-Host "Contenido encontrado dentro de dist:" -ForegroundColor Yellow
  if (Test-Path $DistRoot) {
    Get-ChildItem -Path $DistRoot -Recurse -ErrorAction SilentlyContinue |
      Select-Object FullName, Length, LastWriteTime |
      Format-Table -AutoSize |
      Out-String |
      Write-Host
  } else {
    Write-Host "No existe la carpeta dist: $DistRoot" -ForegroundColor Red
  }
  throw "No se encontrÃ³ arkea-backend.exe dentro de dist. PyInstaller no generÃ³ el backend esperado."
}

$CompiledBackendDir = Split-Path -Parent $CompiledExe
Write-Host "Backend bundle usado: $CompiledBackendDir" -ForegroundColor Green

Start-Backend-Test -ExePath $CompiledExe -Cwd $CompiledBackendDir -Port 7219 -LogDir (Join-Path $Work "backend_test_logs")

Write-Host "[6/9] Preparando Electron Desktop..." -ForegroundColor Green
$Desktop = Join-Path $Ody "desktop"
New-Item -ItemType Directory -Force -Path $Desktop | Out-Null
$BackendDist = Join-Path $Desktop "backend-dist"
if (Test-Path $BackendDist) { Remove-Item $BackendDist -Recurse -Force }
New-Item -ItemType Directory -Force -Path $BackendDist | Out-Null

# main.js espera esta ruta fija:
# backend-dist\arkea-backend\arkea-backend.exe
# Por eso copiamos el bundle real encontrado a esa carpeta normalizada.
$BackendNormalizedDir = Join-Path $BackendDist "arkea-backend"
New-Item -ItemType Directory -Force -Path $BackendNormalizedDir | Out-Null
Copy-Item -Path (Join-Path $CompiledBackendDir "*") -Destination $BackendNormalizedDir -Recurse -Force

if (-not (Test-Path (Join-Path $BackendNormalizedDir "arkea-backend.exe"))) {
  Write-Host "Contenido copiado a backend-dist:" -ForegroundColor Yellow
  Get-ChildItem -Path $BackendNormalizedDir -Recurse -ErrorAction SilentlyContinue |
    Select-Object FullName, Length |
    Format-Table -AutoSize |
    Out-String |
    Write-Host
  throw "No se copiÃ³ arkea-backend.exe a backend-dist\arkea-backend"
}

$AssetsDir = Join-Path $Desktop "assets"
New-Item -ItemType Directory -Force -Path $AssetsDir | Out-Null
Copy-Item -Path (Join-Path $Ody "frontend\assets\icon.ico") -Destination (Join-Path $AssetsDir "icon.ico") -Force
Copy-Item -Path (Join-Path $Ody "frontend\assets\arkea-logo.svg") -Destination (Join-Path $AssetsDir "arkea-logo.svg") -Force

$OllamaBundledDir = Join-Path $Desktop "ollama"
New-Item -ItemType Directory -Force -Path $OllamaBundledDir | Out-Null
$OllamaSetup = Join-Path $OllamaBundledDir "OllamaSetup.exe"
try {
  Write-Host "Descargando instalador oficial de Ollama para incluirlo en el instalador de ARKEA..." -ForegroundColor Green
  Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $OllamaSetup -UseBasicParsing -TimeoutSec 120
} catch {
  Write-Host "No se pudo incluir OllamaSetup.exe. La app abrirÃ¡ el enlace oficial si hace falta." -ForegroundColor Yellow
}

if (Test-Path $OllamaSetup) { Copy-Item -Path $OllamaSetup -Destination (Join-Path $AssetsDir "OllamaSetup.exe") -Force }

$MainJs = @'
const { app, BrowserWindow, dialog, shell, ipcMain, session, desktopCapturer } = require('electron');
const { spawn, execFile } = require('child_process');
const path = require('path');
const http = require('http');
const fs = require('fs');

let backendProcess = null;
const PORT = 7210;

function ensureDir(p) { fs.mkdirSync(p, { recursive: true }); }

function logBootstrap(msg) {
  try {
    const dir = path.join(app.getPath('userData'), 'logs');
    ensureDir(dir);
    fs.appendFileSync(path.join(dir, 'bootstrap.log'), `[${new Date().toISOString()}] ${msg}
`);
  } catch {}
}

function backendExecutablePath() {
  const base = app.isPackaged
    ? path.join(process.resourcesPath, 'backend-dist', 'arkea-backend')
    : path.join(__dirname, 'backend-dist', 'arkea-backend');
  return process.platform === 'win32' ? path.join(base, 'arkea-backend.exe') : path.join(base, 'arkea-backend');
}

function ollamaCandidates() {
  const local = process.env.LOCALAPPDATA || '';
  const pf = process.env.ProgramFiles || '';
  const pfx86 = process.env['ProgramFiles(x86)'] || '';
  const home = app.getPath('home');
  const c = [];
  if (local) c.push(path.join(local, 'Programs', 'Ollama', 'ollama.exe'), path.join(local, 'Ollama', 'ollama.exe'));
  if (pf) c.push(path.join(pf, 'Ollama', 'ollama.exe'));
  if (pfx86) c.push(path.join(pfx86, 'Ollama', 'ollama.exe'));
  c.push(path.join(home, 'AppData', 'Local', 'Programs', 'Ollama', 'ollama.exe'));
  return c;
}

function findOllamaExe() {
  for (const p of ollamaCandidates()) {
    try { if (fs.existsSync(p)) return p; } catch {}
  }
  return 'ollama';
}

function requestJSON(method, url, body, timeoutMs = 120000) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const data = body ? Buffer.from(JSON.stringify(body)) : null;
    const req = http.request({
      hostname: u.hostname,
      port: u.port,
      path: u.pathname + u.search,
      method,
      headers: data ? {'Content-Type':'application/json','Content-Length':data.length} : {},
      timeout: timeoutMs
    }, res => {
      let chunks = '';
      res.on('data', d => chunks += d);
      res.on('end', () => {
        try { resolve(chunks ? JSON.parse(chunks) : {}); }
        catch { resolve({raw: chunks}); }
      });
    });
    req.on('timeout', () => { req.destroy(new Error('timeout')); });
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

function ollamaServerOk(timeoutMs = 650) {
  return new Promise(resolve => {
    const req = http.get('http://127.0.0.1:11434/api/tags', {timeout: timeoutMs}, res => {
      res.resume();
      resolve(res.statusCode === 200);
    });
    req.on('timeout', () => { req.destroy(); resolve(false); });
    req.on('error', () => resolve(false));
  });
}

function startOllamaServe() {
  try {
    const exe = findOllamaExe();
    spawn(exe, ['serve'], {detached:true, stdio:'ignore', windowsHide:true}).unref();
    logBootstrap('ollama serve lanzado: ' + exe);
    return true;
  } catch(e) {
    logBootstrap('no se pudo lanzar ollama serve: ' + e.message);
    return false;
  }
}

function bundledOllamaInstaller() {
  const candidates = [
    path.join(process.resourcesPath || __dirname, 'ollama', 'OllamaSetup.exe'),
    path.join(__dirname, 'ollama', 'OllamaSetup.exe'),
    path.join(__dirname, 'assets', 'OllamaSetup.exe')
  ];
  return candidates.find(p => fs.existsSync(p)) || '';
}

async function installBundledOllamaInternal() {
  const already = findOllamaExe();
  if (already && already !== 'ollama' && fs.existsSync(already)) {
    startOllamaServe();
    return {ok:true, already:true, path:already};
  }

  const installer = bundledOllamaInstaller();
  if (installer) {
    logBootstrap('ejecutando instalador incluido de Ollama: ' + installer);
    try {
      // Intento silencioso. Si el instalador no acepta /S, Windows lo abrirÃ¡ normal.
      spawn(installer, ['/S'], {detached:true, stdio:'ignore', windowsHide:false}).unref();
      return {ok:true, installer};
    } catch(e) {
      logBootstrap('fallÃ³ /S, abriendo instalador normal: ' + e.message);
      spawn(installer, [], {detached:true, stdio:'ignore', windowsHide:false}).unref();
      return {ok:true, installer, normal:true};
    }
  }

  shell.openExternal('https://ollama.com/download/windows');
  return {ok:false, fallback:true};
}

function wireDesktopApis() {
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    if (permission === 'media' || permission === 'microphone' || permission === 'camera' || permission === 'audioCapture' || permission === 'display-capture') return callback(true);
    callback(false);
  });
  session.defaultSession.setPermissionCheckHandler((_webContents, permission) => {
    if (permission === 'media' || permission === 'microphone' || permission === 'camera' || permission === 'audioCapture' || permission === 'display-capture') return true;
    return false;
  });
  ipcMain.handle('arkea:select-folder', async () => {
    const r = await dialog.showOpenDialog({ properties: ['openDirectory','createDirectory'] });
    return { canceled: r.canceled, path: r.filePaths?.[0] || '' };
  });
  ipcMain.handle('arkea:select-image', async () => {
    const r = await dialog.showOpenDialog({ properties: ['openFile'], filters: [{ name: 'ImÃ¡genes', extensions: ['png','jpg','jpeg','webp','gif','svg'] }] });
    if (r.canceled || !r.filePaths?.[0]) return { canceled: true };
    const p = r.filePaths[0];
    const ext = path.extname(p).slice(1).toLowerCase() || 'png';
    const mime = ext === 'svg' ? 'image/svg+xml' : `image/${ext === 'jpg' ? 'jpeg' : ext}`;
    const dataUrl = `data:${mime};base64,${fs.readFileSync(p).toString('base64')}`;
    return { canceled: false, path: p, dataUrl };
  });
  ipcMain.handle('arkea:open-path', async (_e, p) => { if (!p) return; return shell.openPath(p); });
  ipcMain.handle('arkea:reveal-path', async (_e, p) => { if (p) shell.showItemInFolder(p); });
  ipcMain.handle('arkea:open-mic-settings', async () => shell.openExternal('ms-settings:privacy-microphone'));
  ipcMain.handle('arkea:open-external', async (_e, u) => { if (u) return shell.openExternal(u); });
ipcMain.handle('arkea:window-action', async (event, action) => { const win = BrowserWindow.fromWebContents(event.sender); if(!win) return {ok:false}; if(action==='minimize') win.minimize(); if(action==='maximize'){ if(win.isMaximized()) win.unmaximize(); else win.maximize(); } if(action==='close') win.close(); return {ok:true}; });
  ipcMain.handle('arkea:install-bundled-ollama', async () => installBundledOllamaInternal());

  ipcMain.handle('arkea:list-screen-sources', async () => {
    try {
      const sources = await desktopCapturer.getSources({ types: ['screen', 'window'], thumbnailSize: { width: 640, height: 360 } });
      return { sources: sources.map(s => ({ id: s.id, name: s.name, thumbnail: s.thumbnail.toDataURL() })) };
    } catch (e) { return { error: e.message, sources: [] }; }
  });

  ipcMain.handle('arkea:capture-screen-source', async (_e, id) => {
    try {
      const sources = await desktopCapturer.getSources({ types: ['screen', 'window'], thumbnailSize: { width: 1600, height: 900 } });
      const src = sources.find(s => s.id === id) || sources[0];
      if (!src) return { canceled: true, error: 'No hay fuentes disponibles.' };
      return { canceled: false, id: src.id, name: src.name, dataUrl: src.thumbnail.toDataURL() };
    } catch (e) { return { canceled: true, error: e.message }; }
  });

  ipcMain.handle('arkea:capture-screen', async () => {
    const sources = await desktopCapturer.getSources({ types: ['screen', 'window'], thumbnailSize: { width: 1600, height: 900 } });
    if (!sources.length) return { canceled: true, error: 'No hay pantallas o ventanas disponibles.' };
    const src = sources[0];
    return { canceled: false, name: src.name, dataUrl: src.thumbnail.toDataURL() };
  });
}

function startBackend() {
  const exe = backendExecutablePath();
  const userData = app.getPath('userData');
  const docs = app.getPath('documents');
  const logDir = path.join(userData, 'logs');
  ensureDir(logDir);
  const outLog = path.join(logDir, 'backend-out.log');
  const errLog = path.join(logDir, 'backend-err.log');
  const env = {
    ...process.env,
    PYTHONUTF8: '1',
    ARKEA_HOST: '127.0.0.1',
    ARKEA_PORT: String(PORT),
    ARKEA_DATA_DIR: path.join(userData, 'data'),
    ARKEA_DB_PATH: path.join(userData, 'data', 'arkea.db'),
    ARKEA_WORKSPACE: path.join(docs, 'Arkea AI', 'Projects'),
    ARKEA_OBSIDIAN_VAULT: path.join(docs, 'Arkea AI', 'ObsidianVault')
  };
  if (!fs.existsSync(exe)) throw new Error(`No existe el backend: ${exe}`);
  backendProcess = spawn(exe, [], { cwd: path.dirname(exe), env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  backendProcess.stdout.on('data', d => fs.appendFileSync(outLog, d));
  backendProcess.stderr.on('data', d => fs.appendFileSync(errLog, d));
  backendProcess.on('exit', code => fs.appendFileSync(errLog, `
BACKEND EXIT CODE: ${code}
`));
  return { exe, outLog, errLog };
}

function waitForServer(url, timeoutMs = 60000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      http.get(url, res => { res.resume(); resolve(true); })
        .on('error', () => {
          if (Date.now() - start > timeoutMs) reject(new Error('Backend no iniciÃ³ a tiempo'));
          else setTimeout(tick, 650);
        });
    };
    tick();
  });
}

async function autoBootstrapAfterBackend() {
  // Corre en segundo plano: no bloquea la ventana ni el chat.
  try {
    logBootstrap('auto bootstrap iniciado');
    const ok = await ollamaServerOk(500);
    if (!ok) {
      await installBundledOllamaInternal();
      startOllamaServe();
    }
    // dar una ventana corta para que Ollama arranque, sin congelar la app
    for (let i=0; i<12; i++) {
      if (await ollamaServerOk(500)) break;
      await new Promise(r => setTimeout(r, 800));
    }
    // Preparar Whisper tiny y pack de modelos, en segundo plano
    try { await requestJSON('POST', `http://127.0.0.1:${PORT}/api/arkea/voice/install-whisper`, null, 600000); logBootstrap('whisper tiny preparado'); }
    catch(e) { logBootstrap('whisper pendiente: ' + e.message); }
    try { await requestJSON('POST', `http://127.0.0.1:${PORT}/api/arkea/ollama/pull-required`, null, 7200000); logBootstrap('pack minimo procesado'); }
    catch(e) { logBootstrap('pack minimo pendiente: ' + e.message); }
  } catch(e) {
    logBootstrap('auto bootstrap error: ' + e.message);
  }
}

async function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 920,
    title: 'ARKEA AI',
    backgroundColor: '#030712',
    icon: path.join(__dirname, 'assets', 'icon.ico'),
    webPreferences: { contextIsolation: true, nodeIntegration: false, preload: path.join(__dirname, 'preload.js') }
  });
  let info;
  try {
    info = startBackend();
    await waitForServer(`http://127.0.0.1:${PORT}/api/health`);
    await win.loadURL(`http://127.0.0.1:${PORT}`);
    autoBootstrapAfterBackend(); // no await
  } catch (err) {
    const logHint = info ? `

Backend:
${info.exe}

Logs:
${info.errLog}
${info.outLog}` : '';
    dialog.showErrorBox('ARKEA AI', `No se pudo iniciar el backend local.

${err.message}${logHint}`);
    if (info && info.errLog) shell.showItemInFolder(info.errLog);
  }
}

app.whenReady().then(() => { wireDesktopApis(); createWindow(); });
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('before-quit', () => { if (backendProcess) backendProcess.kill(); });

'@
Write-Utf8NoBom (Join-Path $Desktop "main.js") $MainJs

$PreloadJs = @'
const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('arkeaDesktop', {
  selectFolder: () => ipcRenderer.invoke('arkea:select-folder'),
  selectImage: () => ipcRenderer.invoke('arkea:select-image'),
  openPath: (p) => ipcRenderer.invoke('arkea:open-path', p),
  revealPath: (p) => ipcRenderer.invoke('arkea:reveal-path', p),
  captureScreen: () => ipcRenderer.invoke('arkea:capture-screen'),
  listScreenSources: () => ipcRenderer.invoke('arkea:list-screen-sources'),
  captureScreenSource: (id) => ipcRenderer.invoke('arkea:capture-screen-source', id),
  openExternal: (u) => ipcRenderer.invoke('arkea:open-external', u),
  windowAction: (action) => ipcRenderer.invoke('arkea:window-action', action),
  openMicSettings: () => ipcRenderer.invoke('arkea:open-mic-settings'),
  installBundledOllama: () => ipcRenderer.invoke('arkea:install-bundled-ollama')
});
'@
Write-Utf8NoBom (Join-Path $Desktop "preload.js") $PreloadJs

$PackageJson = @'
{
  "name": "arkea-ai",
  "version": "1.0.0",
  "description": "ARKEA AI final ejecutable unpacked estable",
  "main": "main.js",
  "author": "ARKEA",
  "license": "MIT",
  "scripts": {
    "dist:dir": "electron-builder --win --x64 --dir"
  },
  "devDependencies": {
    "electron": "^31.0.0",
    "electron-builder": "^24.13.3"
  },
  "build": {
    "appId": "com.arkea.ai",
    "productName": "ARKEA AI",
    "asar": true,
    "files": [
      "main.js",
      "preload.js",
      "package.json",
      "assets/**/*"
    ],
    "extraResources": [
      { "from": "backend-dist", "to": "backend-dist" },
      { "from": "ollama", "to": "ollama" }
    ],
    "directories": { "output": "dist" },
    "win": {
      "icon": "assets/icon.ico"
    }
  }
}
'@
Write-Utf8NoBom (Join-Path $Desktop "package.json") $PackageJson

Write-Host "[7/9] Instalando dependencias Electron..." -ForegroundColor Green
Set-Location $Desktop
npm.cmd install

Write-Host "[8/9] Construyendo app Windows unpacked estable..." -ForegroundColor Green
$ElectronBuilder = Join-Path $Desktop "node_modules\.bin\electron-builder.cmd"
if (-not (Test-Path $ElectronBuilder)) { throw "No se encontrÃ³ electron-builder local: $ElectronBuilder" }

$Dist = Join-Path $Desktop "dist"
if (Test-Path $Dist) { Remove-Item $Dist -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Dist | Out-Null

# IMPORTANTE:
# Ya NO se usa target portable ni NSIS porque en tu PC fallÃ³ con macros x64_app_files.
# Se usa --dir para generar una carpeta ejecutable real: win-unpacked\ARKEA AI.exe
& $ElectronBuilder --win --x64 --dir
if ($LASTEXITCODE -ne 0) { throw "FallÃ³ la construcciÃ³n unpacked estable (--dir). Revisa el log anterior de electron-builder." }

Write-Host "[9/9] Copiando app ejecutable estable a release..." -ForegroundColor Green
if (Test-Path $Release) { Get-ChildItem -Path $Release -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Force -Path $Release | Out-Null

$WinUnpacked = Join-Path $Dist "win-unpacked"
if (-not (Test-Path $WinUnpacked)) {
  Write-Host "No se encontrÃ³ win-unpacked. Contenido de dist:" -ForegroundColor Red
  Get-ChildItem -Path $Dist -Force | Select-Object Name,Length,LastWriteTime | Format-Table
  throw "No se creÃ³ dist\win-unpacked"
}

$AppExe = Get-ChildItem -Path $WinUnpacked -Filter "*.exe" -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -notmatch "(?i)uninstall|uninstaller" } |
  Sort-Object Length -Descending |
  Select-Object -First 1

if (-not $AppExe) {
  Get-ChildItem -Path $WinUnpacked -Force | Select-Object Name,Length,LastWriteTime | Format-Table
  throw "No se encontrÃ³ el EXE real dentro de win-unpacked"
}

$FinalAppDir = Join-Path $Release "ARKEA-AI-APP"
Copy-Item -Path $WinUnpacked -Destination $FinalAppDir -Recurse -Force

$FinalExe = Join-Path $FinalAppDir $AppExe.Name
$Launcher = Join-Path $Release "ABRIR_ARKEA_AI.bat"
$ExeName = $AppExe.Name
$LauncherContent = @"
@echo off
set "APPDIR=%~dp0ARKEA-AI-APP"
cd /d "%APPDIR%"
start "ARKEA AI" "%APPDIR%\$ExeName"
"@
Write-Utf8NoBom $Launcher $LauncherContent

$LauncherCmd = Join-Path $Release "ABRIR_ARKEA_AI.cmd"
Write-Utf8NoBom $LauncherCmd $LauncherContent

$ReadMeRun = Join-Path $Release "LEER_PARA_ABRIR.txt"
$ReadMeRunContent = @"
ARKEA AI se generÃ³ como APP ejecutable estable, no como instalador.

ABRE UNO DE ESTOS:
1) release\ABRIR_ARKEA_AI.bat o release\ABRIR_ARKEA_AI.cmd
2) release\ARKEA-AI-APP\$($AppExe.Name)

NO muevas solo el .exe. Debe quedarse junto con la carpeta ARKEA-AI-APP porque ahÃ­ estÃ¡n Electron, backend, recursos y OllamaSetup.
"@
Write-Utf8NoBom $ReadMeRun $ReadMeRunContent

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "LISTO. App ejecutable estable creada:" -ForegroundColor Green
Write-Host $FinalExe -ForegroundColor Yellow
Write-Host "TambiÃ©n puedes abrir:" -ForegroundColor Green
Write-Host $Launcher -ForegroundColor Yellow
Write-Host "NO abras archivos __uninstaller. Ya no se usa portable/NSIS." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
