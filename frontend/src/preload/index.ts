import { contextBridge, ipcRenderer, webUtils } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  getPathForFile: (file: File) => webUtils.getPathForFile(file),
  parseFiles: (filePaths: string[]) => ipcRenderer.invoke('parse-files', filePaths),
  selectFiles: () => ipcRenderer.invoke('select-files'),
  exportJSON: (data: object, defaultName: string) => ipcRenderer.invoke('export-json', data, defaultName),
  exportOFX: (filePaths: string[]) => ipcRenderer.invoke('export-ofx', filePaths),
  onBackendStatus: (callback: (status: string) => void) => {
    ipcRenderer.on('backend-status', (_event, status) => callback(status))
  },
  windowMinimize: () => ipcRenderer.invoke('window-minimize'),
  windowMaximize: () => ipcRenderer.invoke('window-maximize'),
  windowClose: () => ipcRenderer.invoke('window-close'),
  windowIsMaximized: () => ipcRenderer.invoke('window-is-maximized'),
  onWindowMaximized: (callback: (isMaximized: boolean) => void) => {
    ipcRenderer.on('window-maximized', (_event, val) => callback(val))
  },
})
