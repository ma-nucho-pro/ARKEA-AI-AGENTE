const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('arkeaDesktop', {
  selectFolder: () => ipcRenderer.invoke('arkea:select-folder'),
  selectImage: () => ipcRenderer.invoke('arkea:select-image'),
  captureScreen: () => ipcRenderer.invoke('arkea:capture-screen'),
  listScreenSources: () => ipcRenderer.invoke('arkea:list-screen-sources'),
  captureScreenSource: (id) => ipcRenderer.invoke('arkea:capture-screen-source', id),
  openPath: (p) => ipcRenderer.invoke('arkea:open-path', p),
  revealPath: (p) => ipcRenderer.invoke('arkea:reveal-path', p),
  openExternal: (u) => ipcRenderer.invoke('arkea:open-external', u),
  openMicSettings: () => ipcRenderer.invoke('arkea:open-mic-settings'),
  installBundledOllama: () => ipcRenderer.invoke('arkea:install-bundled-ollama'),
  omnirouteStatus: () => ipcRenderer.invoke('arkea:omniroute-status'),
  installOmniroute: () => ipcRenderer.invoke('arkea:install-omniroute'),
  startOmniroute: () => ipcRenderer.invoke('arkea:start-omniroute'),
  openOmniroute: () => ipcRenderer.invoke('arkea:open-omniroute'),
  onOmnirouteProgress: (callback) => {
    const listener = (_event, payload) => callback(payload);
    ipcRenderer.on('arkea:omniroute-progress', listener);
    return () => ipcRenderer.removeListener('arkea:omniroute-progress', listener);
  },
  windowAction: (action) => ipcRenderer.invoke('arkea:window-action', action)
});
