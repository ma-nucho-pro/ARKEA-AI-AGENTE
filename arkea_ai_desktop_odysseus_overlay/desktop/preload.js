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
  windowAction: (action) => ipcRenderer.invoke('arkea:window-action', action)
});
