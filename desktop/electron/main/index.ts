import {
  app, BrowserWindow, shell, ipcMain, Tray, Menu, Notification, nativeImage, globalShortcut,
} from 'electron'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import fs from 'node:fs'
import { spawn, ChildProcess } from 'child_process'

const require = createRequire(import.meta.url)
const __dirname = path.dirname(fileURLToPath(import.meta.url))

process.env.APP_ROOT = path.join(__dirname, '../..')

export const MAIN_DIST = path.join(process.env.APP_ROOT, 'dist-electron')
export const RENDERER_DIST = path.join(process.env.APP_ROOT, 'dist')
export const VITE_DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL

process.env.VITE_PUBLIC = VITE_DEV_SERVER_URL
  ? path.join(process.env.APP_ROOT, 'public')
  : RENDERER_DIST

// ── Python 子进程管理 ──────────────────────────

const PYTHON_PORT = 8001
let pythonProcess: ChildProcess | null = null

function startPythonBackend(): Promise<void> {
  const isDev = !!VITE_DEV_SERVER_URL || !app.isPackaged
  const pythonCmd = isDev ? 'python' : path.join(process.resourcesPath, 'backend', 'dailybot-backend.exe')
  const args = isDev
    ? [path.join(process.env.APP_ROOT!, '..', 'serve.py'), '--port', String(PYTHON_PORT)]
    : ['--port', String(PYTHON_PORT)]

  const cwd = isDev ? path.join(process.env.APP_ROOT!, '..') : process.resourcesPath
  console.log(`[Electron] 启动 Python 后端: ${pythonCmd} ${args.join(' ')} (cwd: ${cwd})`)

  pythonProcess = spawn(pythonCmd, args, {
    cwd,
    stdio: ['pipe', 'pipe', 'pipe'],
    shell: process.platform === 'win32',
    env: {
      ...process.env,
      PYTHONIOENCODING: 'utf-8',
    },
  })

  const textDecoder = new TextDecoder('utf-8')

  pythonProcess.stdout?.on('data', (data: Buffer) => {
    const text = textDecoder.decode(data, { stream: true })
    for (const line of text.split('\n').filter(Boolean)) {
      console.log(`[Python] ${line.trim()}`)
    }
  })
  pythonProcess.stderr?.on('data', (data: Buffer) => {
    const text = textDecoder.decode(data, { stream: true })
    for (const line of text.split('\n').filter(Boolean)) {
      console.error(`[Python:err] ${line.trim()}`)
    }
  })
  pythonProcess.on('exit', (code) => {
    console.log(`[Electron] Python 进程退出 (code: ${code})`)
    pythonProcess = null
  })

  return waitForBackend()
}

async function waitForBackend(): Promise<void> {
  const maxRetries = 30
  for (let i = 0; i < maxRetries; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${PYTHON_PORT}/health`)
      if (res.ok) {
        console.log(`[Electron] Python 后端就绪 (尝试 ${i + 1} 次)`)
        return
      }
    } catch { /* 后端尚未就绪 */ }
    await new Promise(r => setTimeout(r, 1000))
  }
  console.warn('[Electron] Python 后端启动超时，继续启动窗口')
}

function stopPythonBackend() {
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
  }
}

// ── 窗口状态持久化 ──────────────────────────

interface WindowState {
  x?: number; y?: number
  width: number; height: number
  isMaximized: boolean
}

const STATE_PATH = path.join(app.getPath('userData'), 'window-state.json')

function loadWindowState(): WindowState {
  try {
    if (fs.existsSync(STATE_PATH)) {
      return JSON.parse(fs.readFileSync(STATE_PATH, 'utf-8'))
    }
  } catch { /* 忽略损坏文件 */ }
  return { width: 1200, height: 800, isMaximized: false }
}

function saveWindowState(win: BrowserWindow) {
  const isMaxed = win.isMaximized()
  if (!isMaxed) {
    const bounds = win.getBounds()
    const state: WindowState = { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height, isMaximized: false }
    try { fs.writeFileSync(STATE_PATH, JSON.stringify(state)) } catch { /* 忽略 */ }
  } else {
    const state: WindowState = { width: 1200, height: 800, isMaximized: true }
    try { fs.writeFileSync(STATE_PATH, JSON.stringify(state)) } catch { /* 忽略 */ }
  }
}

// ── 系统托盘 ──

let tray: Tray | null = null

function createTray(mainWindow: BrowserWindow) {
  const icon = nativeImage.createEmpty()
  tray = new Tray(icon)

  const ctxMenu = Menu.buildFromTemplate([
    {
      label: '打开 DailyBot',
      click: () => {
        mainWindow.show()
        mainWindow.focus()
      },
    },
    {
      label: '立即执行日报',
      click: async () => {
        try {
          await fetch(`http://127.0.0.1:${PYTHON_PORT}/admin/trigger?key=dailybot-admin`, { method: 'POST' })
          new Notification({ title: 'DailyBot', body: '日报生成任务已提交' }).show()
        } catch {
          new Notification({ title: 'DailyBot', body: '执行失败：后端未连接' }).show()
        }
      },
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        app.isQuitting = true
        app.quit()
      },
    },
  ])

  tray.setToolTip('DailyBot 小奕')
  tray.setContextMenu(ctxMenu)
  tray.on('double-click', () => {
    mainWindow.show()
    mainWindow.focus()
  })
}

// ── 全局快捷键 ──────────────────────────

function registerGlobalShortcuts(win: BrowserWindow) {
  globalShortcut.register('CommandOrControl+Alt+D', () => {
    if (win.isVisible()) {
      win.hide()
    } else {
      win.show()
      win.focus()
    }
  })
}

// ── 窗口管理 ──

let win: BrowserWindow | null = null
const preload = path.join(__dirname, '../preload/index.mjs')
const indexHtml = path.join(RENDERER_DIST, 'index.html')

declare const app: Electron.App & { isQuitting?: boolean }

async function createWindow() {
  const savedState = loadWindowState()

  const winOptions: Electron.BrowserWindowConstructorOptions = {
    title: 'DailyBot 小奕',
    width: savedState.width,
    height: savedState.height,
    minWidth: 900,
    minHeight: 600,
    show: false,
    frame: false,
    webPreferences: {
      preload,
      contextIsolation: true,
      nodeIntegration: false,
    },
  }

  // 恢复位置（如果有保存）
  if (savedState.x !== undefined && savedState.y !== undefined) {
    winOptions.x = savedState.x
    winOptions.y = savedState.y
  }

  win = new BrowserWindow(winOptions)

  // 恢复最大化状态
  if (savedState.isMaximized) {
    win.maximize()
  }

  // 开机自启 → 不显示窗口，只驻留托盘
  if (app.getLoginItemSettings().wasOpenedAtLogin) {
    win.once('ready-to-show', () => {
      // 不调用 win.show()，保持隐藏
    })
  } else {
    win.once('ready-to-show', () => {
      win?.show()
    })
  }

  if (VITE_DEV_SERVER_URL) {
    win.loadURL(VITE_DEV_SERVER_URL)
  } else {
    win.loadFile(indexHtml)
  }

  // 关闭：保存窗口状态 + 隐藏到托盘
  win.on('close', (event) => {
    if (win) saveWindowState(win)
    if (!(app as any).isQuitting) {
      event.preventDefault()
      win?.hide()
    }
  })

  // resize/move 防抖保存（避免频繁写磁盘）
  let saveTimer: ReturnType<typeof setTimeout> | null = null
  const debouncedSave = () => {
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(() => { if (win) saveWindowState(win) }, 500)
  }
  win.on('resize', debouncedSave)
  win.on('move', debouncedSave)

  // 最大化状态变更 → 通知渲染进程
  win.on('maximize', () => {
    win?.webContents.send('window-state-changed', true)
  })
  win.on('unmaximize', () => {
    win?.webContents.send('window-state-changed', false)
  })

  // 外部链接用浏览器打开
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https:')) shell.openExternal(url)
    return { action: 'deny' }
  })
}

// ── IPC 处理 ──

ipcMain.handle('window-minimize', () => { win?.minimize() })
ipcMain.handle('window-maximize', () => {
  if (win?.isMaximized()) win.unmaximize()
  else win?.maximize()
})
ipcMain.handle('window-close', () => { win?.close() })
ipcMain.handle('window-is-maximized', () => win?.isMaximized() ?? false)

ipcMain.handle('set-auto-launch', (_event, enabled: boolean) => {
  app.setLoginItemSettings({ openAtLogin: enabled })
  return true
})
ipcMain.handle('get-auto-launch', () => {
  return app.getLoginItemSettings().openAtLogin
})

ipcMain.handle('show-notification', (_event, title: string, body: string) => {
  new Notification({ title, body }).show()
})

// ── 后端进程看守（看门狗） ──────────────────────────

let watchdogTimer: ReturnType<typeof setInterval> | null = null

function startWatchdog() {
  watchdogTimer = setInterval(async () => {
    try {
      const res = await fetch(`http://127.0.0.1:${PYTHON_PORT}/health`)
      if (!res.ok && !pythonProcess) {
        console.warn('[看门狗] 后端无响应且进程已退出，尝试重启...')
        await startPythonBackend()
        new Notification({ title: 'DailyBot', body: '后端服务已自动重启' }).show()
      }
    } catch {
      if (!pythonProcess) {
        console.warn('[看门狗] 后端连接失败且进程已退出，尝试重启...')
        await startPythonBackend()
        new Notification({ title: 'DailyBot', body: '后端服务已自动重启' }).show()
      }
    }
  }, 30000)
}

function stopWatchdog() {
  if (watchdogTimer) {
    clearInterval(watchdogTimer)
    watchdogTimer = null
  }
}

// ── 定期自维护（每 24 小时） ──────────────────────────

let maintenanceTimer: ReturnType<typeof setInterval> | null = null
let maintenanceDelayTimer: ReturnType<typeof setTimeout> | null = null

async function runMaintenance() {
  console.log('[维护] 开始 24 小时定期维护...')
  try {
    // 1. 触发后端 VACUUM + 清理
    const res = await fetch(`http://127.0.0.1:${PYTHON_PORT}/admin/maintenance/auto`, {
      method: 'POST',
      headers: { 'X-Desktop-Client': 'true' },
    })
    const data = await res.json()
    console.log(`[维护] 后端维护完成: ${data.message}`)
  } catch (e) {
    console.warn(`[维护] 后端维护失败（下次重试）: ${e}`)
  }

  try {
    // 2. 清理 Electron 渲染进程缓存
    if (win) {
      win.webContents.session.clearCache()
      console.log('[维护] 渲染进程缓存已清理')
    }
  } catch (e) {
    console.warn(`[维护] 缓存清理失败: ${e}`)
  }
}

function startMaintenanceTimer() {
  // 启动后先等 1 小时再首次执行（给应用稳定时间）
  maintenanceDelayTimer = setTimeout(() => {
    runMaintenance()
    maintenanceTimer = setInterval(runMaintenance, 24 * 60 * 60 * 1000)
  }, 60 * 60 * 1000)
}

function stopMaintenanceTimer() {
  if (maintenanceDelayTimer) {
    clearTimeout(maintenanceDelayTimer)
    maintenanceDelayTimer = null
  }
  if (maintenanceTimer) {
    clearInterval(maintenanceTimer)
    maintenanceTimer = null
  }
}

// ── 应用生命周期 ──

app.whenReady().then(async () => {
  await startPythonBackend()
  createWindow()
  if (win) {
    createTray(win)
    registerGlobalShortcuts(win)
  }
  startWatchdog()
  startMaintenanceTimer()
})

app.on('window-all-closed', () => {
  // 不退出，托盘还在
})

app.on('before-quit', () => {
  stopMaintenanceTimer()
  stopWatchdog()
  globalShortcut.unregisterAll()
  (app as any).isQuitting = true
  stopPythonBackend()
})

app.on('second-instance', () => {
  if (win) {
    if (win.isMinimized()) win.restore()
    win.focus()
  }
})

app.on('activate', () => {
  const allWindows = BrowserWindow.getAllWindows()
  if (allWindows.length) {
    allWindows[0].focus()
  } else {
    createWindow()
  }
})
