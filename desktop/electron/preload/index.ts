import { ipcRenderer, contextBridge } from 'electron'

// ── 窗口控制 API ──────────────────────────
contextBridge.exposeInMainWorld('windowControls', {
  minimize: () => ipcRenderer.invoke('window-minimize'),
  maximize: () => ipcRenderer.invoke('window-maximize'),
  close: () => ipcRenderer.invoke('window-close'),
  isMaximized: () => ipcRenderer.invoke('window-is-maximized'),
  onMaximizeChange: (callback: (maximized: boolean) => void) => {
    ipcRenderer.on('window-state-changed', (_event, maximized) => callback(maximized))
  },
})

// ── 系统 API ──────────────────────────
contextBridge.exposeInMainWorld('electronAPI', {
  setAutoLaunch: (enabled: boolean) => ipcRenderer.invoke('set-auto-launch', enabled),
  getAutoLaunch: () => ipcRenderer.invoke('get-auto-launch'),
})
