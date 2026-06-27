/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface WindowControls {
  minimize: () => Promise<void>
  maximize: () => Promise<void>
  close: () => Promise<void>
  isMaximized: () => Promise<boolean>
  onMaximizeChange: (callback: (maximized: boolean) => void) => void
}

interface ElectronAPI {
  setAutoLaunch: (enabled: boolean) => Promise<boolean>
  getAutoLaunch: () => Promise<boolean>
  showNotification: (title: string, body: string) => Promise<void>
}

interface Window {
  windowControls: WindowControls
  electronAPI: ElectronAPI
}
