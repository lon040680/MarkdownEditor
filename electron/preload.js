const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  openFile: () => ipcRenderer.invoke('dialog:openFile'),
  saveFileAs: () => ipcRenderer.invoke('dialog:saveFileAs'),
  exportPdf: (defaultPath) => ipcRenderer.invoke('dialog:exportPdf', defaultPath),
  exportHtml: (defaultPath) => ipcRenderer.invoke('dialog:exportHtml', defaultPath),
  getFilePath: () => ipcRenderer.invoke('get-file-path'),
  exit: () => ipcRenderer.invoke('app:exit')
})
