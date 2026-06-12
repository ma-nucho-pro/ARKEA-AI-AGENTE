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
      // Intento silencioso. Si el instalador no acepta /S, Windows lo abrirá normal.
      spawn(installer, ['/S'], {detached:true, stdio:'ignore', windowsHide:false}).unref();
      return {ok:true, installer};
    } catch(e) {
      logBootstrap('falló /S, abriendo instalador normal: ' + e.message);
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
    const r = await dialog.showOpenDialog({ properties: ['openFile'], filters: [{ name: 'Imágenes', extensions: ['png','jpg','jpeg','webp','gif','svg'] }] });
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
  backendProcess.on('exit', code => fs.appendFileSync(errLog, `\nBACKEND EXIT CODE: ${code}\n`));
  return { exe, outLog, errLog };
}

function waitForServer(url, timeoutMs = 60000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      http.get(url, res => { res.resume(); resolve(true); })
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
    const logHint = info ? `\n\nBackend:\n${info.exe}\n\nLogs:\n${info.errLog}\n${info.outLog}` : '';
    dialog.showErrorBox('ARKEA AI', `No se pudo iniciar el backend local.\n\n${err.message}${logHint}`);
    if (info && info.errLog) shell.showItemInFolder(info.errLog);
  }
}

app.whenReady().then(() => { wireDesktopApis(); createWindow(); });
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('before-quit', () => { if (backendProcess) backendProcess.kill(); });


ipcMain.handle('arkea:window-action', async (event, action) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  if (!win) return {ok:false};
  if (action === 'minimize') win.minimize();
  if (action === 'maximize') { if (win.isMaximized()) win.unmaximize(); else win.maximize(); }
  if (action === 'close') win.close();
  return {ok:true};
});
