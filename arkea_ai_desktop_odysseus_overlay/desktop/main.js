const { app, BrowserWindow, dialog, shell, ipcMain, session, desktopCapturer, safeStorage } = require('electron');
const { spawn, execFile } = require('child_process');
const path = require('path');
const http = require('http');
const fs = require('fs');
const crypto = require('crypto');
const {shouldAttachArkeaToken} = require('./request_auth');

let backendProcess = null;
let omnirouteProcess = null;
const PORT = 20000 + crypto.randomInt(30000);
const TRUSTED_ORIGIN = `http://127.0.0.1:${PORT}`;
const API_TOKEN = crypto.randomBytes(32).toString('base64url');
const OMNIROUTE = Object.freeze({
  version: '3.8.49',
  port: 20128,
  url: 'https://github.com/diegosouzapw/OmniRoute/releases/download/v3.8.49/OmniRoute.Setup.3.8.49.exe',
  sha256: 'b6f0f209d9a4df9de3a17de8f8f209f6c5dcfa774f3506c6bd2472a17e03100a',
  size: 340441395
});
const OLLAMA_SETUP = Object.freeze({
  version: '0.32.5',
  sha256: 'b7eeef038ddcbd09ac665b11872baff1bc9b42794be41b5ef187b2f4b16a4498',
  size: 1563078600
});

function isTrustedFrame(event) {
  try {
    const frame = event.senderFrame;
    return !!frame && frame === frame.top && new URL(frame.url).origin === TRUSTED_ORIGIN;
  } catch { return false; }
}

function secureHandle(channel, handler) {
  ipcMain.handle(channel, async (event, ...args) => {
    if (!isTrustedFrame(event)) throw new Error('IPC no autorizado');
    return handler(event, ...args);
  });
}

function protectLocalBackendSession() {
  session.defaultSession.webRequest.onBeforeSendHeaders(
    {urls: [`${TRUSTED_ORIGIN}/*`]},
    (details, callback) => {
      for (const name of Object.keys(details.requestHeaders)) {
        if (name.toLowerCase() === 'x-arkea-token') delete details.requestHeaders[name];
      }
      if (shouldAttachArkeaToken(details, TRUSTED_ORIGIN)) {
        details.requestHeaders['X-Arkea-Token'] = API_TOKEN;
      }
      callback({requestHeaders: details.requestHeaders});
    }
  );
}

function safeExternalUrl(value) {
  const url = new URL(String(value || ''));
  if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) throw new Error('URL externa no permitida');
  return url.toString();
}

function safeOpenPath(value) {
  const resolved = path.resolve(String(value || ''));
  if (!path.isAbsolute(resolved) || !fs.existsSync(resolved)) throw new Error('Ruta inexistente o no permitida');
  if (fs.statSync(resolved).isFile() && /\.(exe|com|bat|cmd|ps1|vbs|js|msi|scr|lnk|url)$/i.test(resolved)) {
    throw new Error('No se permite ejecutar este tipo de archivo');
  }
  return resolved;
}

function ensureDir(p) { fs.mkdirSync(p, { recursive: true }); }

function omnirouteRuntimeDir() {
  return path.join(app.getPath('userData'), 'omniroute-runtime');
}

function omnirouteInstallCandidates() {
  const local = process.env.LOCALAPPDATA || '';
  const pf = process.env.ProgramFiles || '';
  const pfx86 = process.env['ProgramFiles(x86)'] || '';
  return [
    local && path.join(local, 'Programs', 'OmniRoute', 'OmniRoute.exe'),
    local && path.join(local, 'Programs', 'omniroute-desktop', 'OmniRoute.exe'),
    local && path.join(local, 'Programs', 'omniroute', 'OmniRoute.exe'),
    local && path.join(local, 'OmniRoute', 'OmniRoute.exe'),
    pf && path.join(pf, 'OmniRoute', 'OmniRoute.exe'),
    pfx86 && path.join(pfx86, 'OmniRoute', 'OmniRoute.exe')
  ].filter(Boolean);
}

function findOmnirouteExecutable() {
  return omnirouteInstallCandidates().find(candidate => {
    try { return fs.statSync(candidate).isFile(); } catch { return false; }
  }) || '';
}

function readOmnirouteExecutableVersion(executable) {
  if (!executable || process.platform !== 'win32') return Promise.resolve('');
  return new Promise(resolve => {
    execFile(
      'powershell.exe',
      ['-NoProfile', '-NonInteractive', '-Command', '(Get-Item -LiteralPath $env:ARKEA_OMNIROUTE_EXE).VersionInfo.FileVersion'],
      {windowsHide:true, timeout:10000, env:{...process.env, ARKEA_OMNIROUTE_EXE:executable}},
      (error, stdout) => resolve(error ? '' : String(stdout || '').trim())
    );
  });
}

function isSupportedOmnirouteVersion(value) {
  const match = String(value || '').match(/^(\d+)\.(\d+)\.(\d+)/);
  if (!match) return false;
  const current = match.slice(1).map(Number);
  const minimum = OMNIROUTE.version.split('.').map(Number);
  for (let index = 0; index < 3; index += 1) {
    if (current[index] > minimum[index]) return true;
    if (current[index] < minimum[index]) return false;
  }
  return true;
}

function emitOmnirouteProgress(payload) {
  for (const win of BrowserWindow.getAllWindows()) {
    if (!win.isDestroyed()) win.webContents.send('arkea:omniroute-progress', payload);
  }
}

function sha256File(filePath) {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash('sha256');
    const input = fs.createReadStream(filePath);
    input.on('error', reject);
    input.on('data', chunk => hash.update(chunk));
    input.on('end', () => resolve(hash.digest('hex')));
  });
}

async function installOmnirouteInternal() {
  const alreadyInstalled = findOmnirouteExecutable();
  if (alreadyInstalled) {
    const installedVersion = await readOmnirouteExecutableVersion(alreadyInstalled);
    if (isSupportedOmnirouteVersion(installedVersion)) {
      emitOmnirouteProgress({phase:'installed', version:installedVersion});
      return {ok:true, already:true, path:alreadyInstalled, version:installedVersion};
    }
    logBootstrap(`OmniRoute ${installedVersion || 'sin versión'} requiere actualizarse a ${OMNIROUTE.version}`);
  }
  const downloadedInstaller = path.join(app.getPath('downloads'), `OmniRoute.Setup.${OMNIROUTE.version}.exe`);
  if (fs.existsSync(downloadedInstaller)) {
    const stat = fs.statSync(downloadedInstaller);
    const digest = await sha256File(downloadedInstaller);
    if (stat.size === OMNIROUTE.size && digest.toLowerCase() === OMNIROUTE.sha256) {
      const openError = await shell.openPath(downloadedInstaller);
      if (openError) throw new Error(`Windows no pudo abrir el instalador oficial: ${openError}`);
      logBootstrap(`instalador oficial de OmniRoute ${OMNIROUTE.version} abierto desde Descargas`);
      emitOmnirouteProgress({phase:'installer-opened', version:OMNIROUTE.version});
      return {ok:true, installerOpened:true, version:OMNIROUTE.version};
    }
    logBootstrap('se ignoró un instalador de OmniRoute en Descargas porque no coincide con SHA-256');
  }
  const answer = await dialog.showMessageBox({
    type: 'info',
    title: `Instalar OmniRoute ${OMNIROUTE.version}`,
    message: 'Se abrirá la descarga oficial de OmniRoute en tu navegador.',
    detail: 'Cuando termine, ejecuta OmniRoute.Setup.3.8.49.exe, completa el asistente y vuelve a ARKEA para pulsar "Detectar e iniciar".',
    buttons: ['Descargar instalador oficial', 'Cancelar'],
    defaultId: 0,
    cancelId: 1,
    noLink: true
  });
  if (answer.response !== 0) return {ok:false, canceled:true, version:OMNIROUTE.version};
  await shell.openExternal(OMNIROUTE.url);
  logBootstrap(`descarga oficial de OmniRoute ${OMNIROUTE.version} abierta en el navegador`);
  emitOmnirouteProgress({phase:'download-page', version:OMNIROUTE.version});
  return {ok:true, downloadOpened:true, version:OMNIROUTE.version};
}

function inspectOmnirouteServer(timeoutMs = 900) {
  const secrets = ensureOmnirouteSecrets();
  const probe = (pathname, authenticated = false) => new Promise(resolve => {
    const req = http.get({
      hostname: '127.0.0.1',
      port: OMNIROUTE.port,
      path: pathname,
      timeout: timeoutMs,
      headers: authenticated ? {Authorization: `Bearer ${secrets.api}`} : {}
    }, res => {
      const chunks = [];
      let received = 0;
      res.on('data', chunk => {
        received += chunk.length;
        if (received <= 2 * 1024 * 1024) chunks.push(chunk);
        else req.destroy();
      });
      res.on('end', () => {
        try { resolve({status:res.statusCode, data:JSON.parse(Buffer.concat(chunks).toString('utf8'))}); }
        catch { resolve({status:res.statusCode, data:null}); }
      });
    });
    req.on('timeout', () => { req.destroy(); resolve(null); });
    req.on('error', () => resolve(null));
  });
  return (async () => {
    const health = await probe('/api/monitoring/health');
    if (!health) return {responding:false, healthy:false, authorized:false, version:''};
    const version = String(health.data?.version || '');
    const healthy = health.status === 200 && health.data?.status === 'healthy' && Boolean(version);
    if (!healthy) return {responding:true, healthy:false, authorized:false, version};
    if (!isSupportedOmnirouteVersion(version)) {
      return {responding:true, healthy:true, supported:false, authorized:false, version};
    }
    const models = await probe('/v1/models', true);
    const authorized = Boolean(models && models.status === 200 && Array.isArray(models.data?.data));
    return {responding:true, healthy:true, supported:true, authorized, version};
  })();
}

async function omnirouteServerOk(timeoutMs = 900) {
  const state = await inspectOmnirouteServer(timeoutMs);
  return state.authorized;
}

function ensureOmnirouteSecrets() {
  const file = path.join(omnirouteRuntimeDir(), 'runtime-secrets.bin');
  const legacyFile = path.join(omnirouteRuntimeDir(), 'runtime-secrets.json');
  const valid = data => data && data.jwt && data.api && data.storage && data.password;
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error('Windows no habilitó DPAPI; no se pueden guardar secretos de OmniRoute de forma segura');
  }
  if (fs.existsSync(file)) {
    try {
      const plaintext = safeStorage.decryptString(fs.readFileSync(file));
      const data = JSON.parse(plaintext);
      if (valid(data)) return data;
    } catch {}
  }
  let data;
  if (fs.existsSync(legacyFile)) {
    try {
      const legacy = JSON.parse(fs.readFileSync(legacyFile, 'utf8'));
      if (valid(legacy)) data = legacy;
    } catch {}
  }
  if (!data) {
    data = {
      jwt: crypto.randomBytes(48).toString('base64url'),
      api: `sk-arkea-${crypto.randomBytes(32).toString('base64url')}`,
      storage: crypto.randomBytes(32).toString('hex'),
      password: crypto.randomBytes(18).toString('base64url')
    };
  }
  ensureDir(path.dirname(file));
  const encrypted = safeStorage.encryptString(JSON.stringify(data));
  fs.writeFileSync(file, encrypted, {mode:0o600});
  try { if (fs.existsSync(legacyFile)) fs.unlinkSync(legacyFile); } catch {}
  return data;
}

async function startOmnirouteInternal({installIfMissing = false} = {}) {
  const existingServer = await inspectOmnirouteServer();
  if (existingServer.authorized) {
    return {
      ok:true,
      running:true,
      owned:Boolean(omnirouteProcess?.pid),
      port:OMNIROUTE.port,
      version:existingServer.version
    };
  }
  if (existingServer.healthy && !existingServer.supported) {
    throw new Error(`OmniRoute ${existingServer.version || 'antiguo'} está abierto. Actualiza a ${OMNIROUTE.version} y ciérralo antes de iniciar desde ARKEA.`);
  }
  if (existingServer.healthy) {
    throw new Error('OmniRoute ya está abierto fuera de ARKEA en el puerto 20128. Ciérralo desde su icono de la bandeja y vuelve a pulsar "Detectar e iniciar".');
  }
  if (existingServer.responding) {
    throw new Error('El puerto 20128 está ocupado por otro programa. Ciérralo antes de iniciar OmniRoute.');
  }
  let executable = findOmnirouteExecutable();
  if (!executable) {
    if (!installIfMissing) return {ok:false, installed:false, message:'OmniRoute todavía no está instalado'};
    await installOmnirouteInternal();
    throw new Error('Completa el instalador oficial de OmniRoute y después pulsa "Detectar e iniciar".');
  }
  if (!executable) throw new Error('No se encontró el ejecutable instalado de OmniRoute');
  const installedVersion = await readOmnirouteExecutableVersion(executable);
  if (!isSupportedOmnirouteVersion(installedVersion)) {
    throw new Error(`Está instalado OmniRoute ${installedVersion || 'sin versión detectable'}. Instala la versión oficial ${OMNIROUTE.version} y vuelve a intentarlo.`);
  }
  const secrets = ensureOmnirouteSecrets();
  const env = {
    ...process.env,
    OMNIROUTE_HEADLESS: 'true',
    OMNIROUTE_SERVER_HOST: '127.0.0.1',
    HOST: '127.0.0.1',
    HOSTNAME: '127.0.0.1',
    ARENA_ELO_SYNC_ENABLED: 'false',
    OMNIROUTE_MEMORY_MB: '4096',
    NODE_OPTIONS: '--max-old-space-size=4096',
    OMNIROUTE_PORT: String(OMNIROUTE.port),
    PORT: String(OMNIROUTE.port),
    LIVE_WS_PORT: String(OMNIROUTE.port + 1),
    REQUIRE_API_KEY: 'true',
    ALLOW_API_KEY_REVEAL: 'false',
    OMNIROUTE_API_KEY: secrets.api,
    ROUTER_API_KEY: secrets.api,
    OMNIROUTE_ALLOW_PRIVATE_PROVIDER_URLS: 'true',
    DATA_DIR: path.join(app.getPath('userData'), 'omniroute-data'),
    JWT_SECRET: secrets.jwt,
    API_KEY_SECRET: secrets.api,
    STORAGE_ENCRYPTION_KEY: secrets.storage,
    INITIAL_PASSWORD: secrets.password
  };
  const logDir = path.join(app.getPath('userData'), 'logs');
  ensureDir(logDir);
  const outLog = path.join(logDir, 'omniroute-out.log');
  const errLog = path.join(logDir, 'omniroute-err.log');
  const child = spawn(executable, ['--headless'], {
    env,
    cwd: path.dirname(executable),
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: false
  });
  omnirouteProcess = child;
  let exitCode = null;
  let exited = false;
  let spawnError = null;
  child.stdout?.on('data', data => fs.appendFileSync(outLog, data));
  child.stderr?.on('data', data => fs.appendFileSync(errLog, data));
  child.once('error', error => { spawnError = error; });
  child.once('exit', code => {
    exited = true;
    exitCode = code;
    logBootstrap(`OmniRoute terminó con código ${code}`);
    if (omnirouteProcess === child) omnirouteProcess = null;
  });
  logBootstrap(`OmniRoute ${installedVersion} iniciado en loopback:${OMNIROUTE.port}`);
  // La primera inicialización crea base de datos y recursos locales. Evitamos
  // sondeos agresivos mientras Next.js carga su instrumentación y catálogo.
  const readinessStartedAt = Date.now();
  while (Date.now() - readinessStartedAt < 6 * 60 * 1000) {
    if (spawnError) throw new Error(`Windows no pudo iniciar OmniRoute: ${spawnError.message}`);
    if (exited) {
      throw new Error(`OmniRoute se cerró al iniciar (código ${exitCode ?? 'desconocido'}). Revisa ${errLog}`);
    }
    const state = await inspectOmnirouteServer(4000);
    if (state.authorized) {
      emitOmnirouteProgress({phase:'running', version:state.version});
      return {ok:true, running:true, installed:true, port:OMNIROUTE.port, version:state.version};
    }
    const elapsedSeconds = Math.round((Date.now() - readinessStartedAt) / 1000);
    if (elapsedSeconds === 0 || elapsedSeconds % 5 < 2) {
      emitOmnirouteProgress({
        phase: 'preparing',
        version: installedVersion,
        elapsedSeconds
      });
    }
    await new Promise(resolve => setTimeout(resolve, 1500));
  }
  throw new Error(`OmniRoute no inició dentro de 6 minutos. Revisa el antivirus y ${errLog}`);
}

function stopOwnedOmniroute() {
  const child = omnirouteProcess;
  if (!child || !child.pid) return;
  const pid = child.pid;
  omnirouteProcess = null;
  try { child.kill(); } catch {}
  if (process.platform === 'win32') {
    execFile('taskkill', ['/pid', String(pid), '/t', '/f'], {windowsHide:true}, () => {});
  }
}

async function omnirouteDesktopStatus() {
  const executable = findOmnirouteExecutable();
  const installedVersion = executable ? await readOmnirouteExecutableVersion(executable) : '';
  const runtime = await inspectOmnirouteServer();
  return {
    ok:true,
    installed:Boolean(executable),
    supported:Boolean(executable) && isSupportedOmnirouteVersion(installedVersion),
    running:runtime.authorized,
    portOccupied:runtime.responding && !runtime.authorized,
    owned:Boolean(omnirouteProcess?.pid),
    version:runtime.version || installedVersion || OMNIROUTE.version,
    targetVersion:OMNIROUTE.version,
    port:OMNIROUTE.port
  };
}

function logBootstrap(msg) {
  try {
    const dir = path.join(app.getPath('userData'), 'logs');
    ensureDir(dir);
    fs.appendFileSync(path.join(dir, 'bootstrap.log'), `[${new Date().toISOString()}] ${msg}\n`);
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
      headers: {...(data ? {'Content-Type':'application/json','Content-Length':data.length} : {}), 'X-Arkea-Token': API_TOKEN},
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
    const stat = fs.statSync(installer);
    const digest = await sha256File(installer);
    if (stat.size !== OLLAMA_SETUP.size || digest.toLowerCase() !== OLLAMA_SETUP.sha256) {
      throw new Error(`El instalador incluido de Ollama ${OLLAMA_SETUP.version} no superó la verificación`);
    }
    logBootstrap(`ejecutando instalador verificado de Ollama ${OLLAMA_SETUP.version}`);
    await new Promise((resolve, reject) => {
      const child = spawn(installer, ['/S'], {stdio:'ignore', windowsHide:true});
      const timer = setTimeout(() => {
        try { child.kill(); } catch {}
        reject(new Error('La instalación de Ollama superó 20 minutos'));
      }, 20 * 60 * 1000);
      child.once('error', error => { clearTimeout(timer); reject(error); });
      child.once('exit', code => {
        clearTimeout(timer);
        if (code === 0) resolve();
        else reject(new Error(`El instalador de Ollama terminó con código ${code}`));
      });
    });
    startOllamaServe();
    for (let i = 0; i < 120; i++) {
      if (await ollamaServerOk(1000)) {
        return {ok:true, installer, version:OLLAMA_SETUP.version};
      }
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    throw new Error('Ollama se instaló pero su servicio local no inició');
  }

  shell.openExternal('https://ollama.com/download/windows');
  return {ok:false, fallback:true};
}

function wireDesktopApis() {
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback, details) => {
    const requestingUrl = details?.requestingUrl || details?.securityOrigin || webContents.getURL();
    let trusted = false;
    try { trusted = new URL(requestingUrl).origin === TRUSTED_ORIGIN && !String(requestingUrl).startsWith('about:'); } catch {}
    if (trusted && (permission === 'media' || permission === 'microphone' || permission === 'camera' || permission === 'audioCapture' || permission === 'display-capture')) return callback(true);
    callback(false);
  });
  session.defaultSession.setPermissionCheckHandler((webContents, permission, requestingOrigin) => {
    let trusted = false;
    try { trusted = new URL(requestingOrigin || webContents.getURL()).origin === TRUSTED_ORIGIN; } catch {}
    if (trusted && (permission === 'media' || permission === 'microphone' || permission === 'camera' || permission === 'audioCapture' || permission === 'display-capture')) return true;
    return false;
  });
  secureHandle('arkea:select-folder', async () => {
    const r = await dialog.showOpenDialog({ properties: ['openDirectory','createDirectory'] });
    return { canceled: r.canceled, path: r.filePaths?.[0] || '' };
  });
  secureHandle('arkea:select-image', async () => {
    const r = await dialog.showOpenDialog({ properties: ['openFile'], filters: [{ name: 'Imágenes', extensions: ['png','jpg','jpeg','webp','gif','svg'] }] });
    if (r.canceled || !r.filePaths?.[0]) return { canceled: true };
    const p = r.filePaths[0];
    const ext = path.extname(p).slice(1).toLowerCase() || 'png';
    const mime = ext === 'svg' ? 'image/svg+xml' : `image/${ext === 'jpg' ? 'jpeg' : ext}`;
    const dataUrl = `data:${mime};base64,${fs.readFileSync(p).toString('base64')}`;
    return { canceled: false, path: p, dataUrl };
  });
  secureHandle('arkea:open-path', async (_e, p) => { if (!p) return; return shell.openPath(safeOpenPath(p)); });
  secureHandle('arkea:reveal-path', async (_e, p) => { if (p) shell.showItemInFolder(safeOpenPath(p)); });
  secureHandle('arkea:open-mic-settings', async () => shell.openExternal('ms-settings:privacy-microphone'));
  secureHandle('arkea:open-external', async (_e, u) => { if (u) return shell.openExternal(safeExternalUrl(u)); });
  secureHandle('arkea:install-bundled-ollama', async () => installBundledOllamaInternal());
  secureHandle('arkea:omniroute-status', async () => omnirouteDesktopStatus());
  secureHandle('arkea:install-omniroute', async () => installOmnirouteInternal());
  secureHandle('arkea:start-omniroute', async () => startOmnirouteInternal({installIfMissing:true}));
  secureHandle('arkea:open-omniroute', async () => {
    const secrets = ensureOmnirouteSecrets();
    await dialog.showMessageBox({
      type: 'info',
      title: 'Acceso local a OmniRoute',
      message: 'Contraseña inicial del panel local',
      detail:
        `${secrets.password}\n\n` +
        'Esta contraseña solo se usa en la primera configuración. Cámbiala dentro del panel. ' +
        'La clave de la API permanece cifrada por Windows y no se muestra.',
      buttons: ['Abrir OmniRoute', 'Cancelar'],
      defaultId: 0,
      cancelId: 1,
      noLink: true
    }).then(result => {
      if (result.response === 0) {
        return shell.openExternal(`http://127.0.0.1:${OMNIROUTE.port}`);
      }
      return undefined;
    });
  });

  secureHandle('arkea:list-screen-sources', async () => {
    try {
      const sources = await desktopCapturer.getSources({ types: ['screen', 'window'], thumbnailSize: { width: 640, height: 360 } });
      return { sources: sources.map(s => ({ id: s.id, name: s.name, thumbnail: s.thumbnail.toDataURL() })) };
    } catch (e) { return { error: e.message, sources: [] }; }
  });

  secureHandle('arkea:capture-screen-source', async (_e, id) => {
    try {
      const sources = await desktopCapturer.getSources({ types: ['screen', 'window'], thumbnailSize: { width: 1600, height: 900 } });
      const src = sources.find(s => s.id === id) || sources[0];
      if (!src) return { canceled: true, error: 'No hay fuentes disponibles.' };
      return { canceled: false, id: src.id, name: src.name, dataUrl: src.thumbnail.toDataURL() };
    } catch (e) { return { canceled: true, error: e.message }; }
  });

  secureHandle('arkea:capture-screen', async () => {
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
  const omniSecrets = ensureOmnirouteSecrets();
  const logDir = path.join(userData, 'logs');
  ensureDir(logDir);
  const outLog = path.join(logDir, 'backend-out.log');
  const errLog = path.join(logDir, 'backend-err.log');
  const env = {
    ...process.env,
    PYTHONUTF8: '1',
    ARKEA_HOST: '127.0.0.1',
    ARKEA_PORT: String(PORT),
    ARKEA_API_TOKEN: API_TOKEN,
    ARKEA_DATA_DIR: path.join(userData, 'data'),
    ARKEA_DB_PATH: path.join(userData, 'data', 'arkea.db'),
    ARKEA_WORKSPACE: path.join(docs, 'ARKEA AI OmniAgent', 'Projects'),
    ARKEA_OBSIDIAN_VAULT: path.join(docs, 'ARKEA AI OmniAgent', 'ObsidianVault'),
    OMNIROUTE_API_KEY: omniSecrets.api
  };
  if (!fs.existsSync(exe)) throw new Error(`No existe el backend: ${exe}`);
  backendProcess = spawn(exe, [], { cwd: path.dirname(exe), env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  backendProcess.stdout.on('data', d => fs.appendFileSync(outLog, d));
  backendProcess.stderr.on('data', d => fs.appendFileSync(errLog, d));
  backendProcess.on('exit', code => fs.appendFileSync(errLog, `\nBACKEND EXIT CODE: ${code}\n`));
  return { exe, outLog, errLog };
}

function waitForServer(url, timeoutMs = 60000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      http.get(url, {headers: {'X-Arkea-Token': API_TOKEN}}, res => {
        let body = '';
        res.on('data', chunk => { if (body.length < 4096) body += chunk; });
        res.on('end', () => {
          try {
            const data = JSON.parse(body);
            if (res.statusCode === 200 && data.ok === true && data.name === 'ARKEA AI Desktop') return resolve(true);
          } catch {}
          if (Date.now() - start > timeoutMs) reject(new Error('El backend local no superó la verificación de identidad'));
          else setTimeout(tick, 650);
        });
      })
        .on('error', () => {
          if (Date.now() - start > timeoutMs) reject(new Error('Backend no inició a tiempo'));
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
    if (findOmnirouteExecutable()) {
      try { await startOmnirouteInternal({installIfMissing:false}); }
      catch(e) { logBootstrap('OmniRoute pendiente: ' + e.message); }
    }
    // Respetar la elección del onboarding: solo iniciar Ollama si el usuario ya
    // lo instaló. La instalación y descarga de modelos ocurre únicamente al
    // pulsar la opción correspondiente.
    const ollamaExecutable = findOllamaExe();
    if (ollamaExecutable !== 'ollama' && fs.existsSync(ollamaExecutable)) {
      if (!(await ollamaServerOk(500))) startOllamaServe();
    } else {
      logBootstrap('Ollama no instalado; esperando elección explícita del usuario');
    }
  } catch(e) {
    logBootstrap('auto bootstrap error: ' + e.message);
  }
}

async function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 980,
    minHeight: 640,
    title: 'ARKEA AI',
    frame: false,
    autoHideMenuBar: true,
    backgroundColor: '#050807',
    icon: path.join(__dirname, 'assets', 'icon.ico'),
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true, webSecurity: true, preload: path.join(__dirname, 'preload.js') }
  });
  win.webContents.on('will-navigate', (event, url) => {
    try { if (new URL(url).origin !== TRUSTED_ORIGIN) event.preventDefault(); } catch { event.preventDefault(); }
  });
  win.webContents.setWindowOpenHandler(({url}) => {
    try { shell.openExternal(safeExternalUrl(url)); } catch {}
    return {action: 'deny'};
  });
  win.webContents.on('will-attach-webview', event => event.preventDefault());
  let info;
  try {
    info = startBackend();
    await waitForServer(`http://127.0.0.1:${PORT}/api/health`);
    await win.loadURL(`http://127.0.0.1:${PORT}`);
    autoBootstrapAfterBackend(); // no await
  } catch (err) {
    const logHint = info ? `\n\nBackend:\n${info.exe}\n\nLogs:\n${info.errLog}\n${info.outLog}` : '';
    dialog.showErrorBox('ARKEA AI', `No se pudo iniciar el backend local.\n\n${err.message}${logHint}`);
    if (info && info.errLog) shell.showItemInFolder(info.errLog);
  }
}

app.whenReady().then(() => {
  protectLocalBackendSession();
  wireDesktopApis();
  createWindow();
});
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('before-quit', () => {
  stopOwnedOmniroute();
  if (backendProcess) backendProcess.kill();
});


secureHandle('arkea:window-action', async (event, action) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  if (!win) return {ok:false};
  if (action === 'minimize') win.minimize();
  if (action === 'maximize') { if (win.isMaximized()) win.unmaximize(); else win.maximize(); }
  if (action === 'close') win.close();
  return {ok:true};
});
