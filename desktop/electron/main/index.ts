import {
  app, BrowserWindow, shell, ipcMain, Tray, Menu, Notification, nativeImage,
} from 'electron'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
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
  })

  pythonProcess.stdout?.on('data', (data: Buffer) => {
    console.log(`[Python] ${data.toString().trim()}`)
  })
  pythonProcess.stderr?.on('data', (data: Buffer) => {
    console.error(`[Python:err] ${data.toString().trim()}`)
  })
  pythonProcess.on('exit', (code) => {
    console.log(`[Electron] Python 进程退出 (code: ${code})`)
    pythonProcess = null
  })

  // 等待后端就绪（健康检查轮询）
  return waitForBackend()
}

async function waitForBackend(): Promise<void> {
  const maxRetries = 30  // 最多 30 秒
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

// ── 系统托盘 ──────────────────────────────────

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

// ── 窗口管理 ──────────────────────────────────

let win: BrowserWindow | null = null
const preload = path.join(__dirname, '../preload/index.mjs')
const indexHtml = path.join(RENDERER_DIST, 'index.html')

declare const app: Electron.App & { isQuitting?: boolean }

async function createWindow() {
  // Windows 11 acrylic 背景
  const winOptions: Electron.BrowserWindowConstructorOptions = {
    title: 'DailyBot 小奕',
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    show: false,
    frame: false,                // 无边框
    transparent: true,           // 透明背景（玻璃效果需要）
    webPreferences: {
      preload,
      contextIsolation: true,
      nodeIntegration: false,
    },
  }

  // Windows 11/10 acrylic 毛玻璃
  if (process.platform === 'win32') {
    winOptions.backgroundMaterial = 'acrylic'
  }

  win = new BrowserWindow(winOptions)

  // 窗口准备好后再显示
  win.once('ready-to-show', () => {
    win?.show()
  })

  if (VITE_DEV_SERVER_URL) {
    win.loadURL(VITE_DEV_SERVER_URL)
    win.webContents.openDevTools()
  } else {
    win.loadFile(indexHtml)
  }

  // 关闭按钮 → 隐藏到托盘
  win.on('close', (event) => {
    if (!(app as any).isQuitting) {
      event.preventDefault()
      win?.hide()
    }
  })

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

// ── IPC 处理 ──────────────────────────────────

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

// ── 应用生命周期 ──────────────────────────────

app.whenReady().then(async () => {
  await startPythonBackend()
  createWindow()
  // 窗口创建后再创建托盘（等一段让 DOM 也准备）
  if (win) createTray(win)
})

app.on('window-all-closed', () => {
  // 不退出，托盘还在
})

app.on('before-quit', () => {
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
