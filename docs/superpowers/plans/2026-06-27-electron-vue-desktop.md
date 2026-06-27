# DailyBot 桌面版改造实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task.

**Goal:** 将 DailyBot 从 CLI + Web 面板混合模式改造为 Electron + Vue 3 桌面工具，保留全部 Python 后端能力，新增系统托盘、实时日志、系统通知、一键配置等桌面原生体验。

**Architecture:** Electron 主进程管理 Python FastAPI 子进程（带健康检查和自动重启），Vue 3 渲染进程通过 REST API 与后端通信。Python 代码零改动三方服务层，仅需新增 `serve.py` 纯 Web 模式入口。SQLite 数据库不变。

**Tech Stack:** Electron 28 + Vue 3.4 + TypeScript + Vite (electron-vite) + Python FastAPI (现有)

---

## 文件结构设计

```
daily-bot/
├── electron/                          # [新增] Electron 层
│   ├── main/
│   │   ├── index.ts                   #   主进程入口：窗口管理 + 子进程管理
│   │   └── tray.ts                    #   系统托盘
│   ├── preload/
│   │   └── index.ts                   #   预加载脚本：安全暴露 API 给渲染进程
│   └── electron.vite.config.ts        #   electron-vite 配置
├── src/                               # [新增] Vue 3 前端
│   ├── main.ts                        #   Vue 应用入口
│   ├── App.vue                        #   根组件：布局框架 + 路由
│   ├── env.d.ts                       #   类型声明
│   ├── api/                           #   API 调用层
│   │   └── client.ts                  #   封装 fetch 调用后端 REST API
│   ├── components/                    #   通用组件
│   │   ├── GlassCard.vue              #   玻璃卡片容器
│   │   ├── StatusBadge.vue            #   状态标签
│   │   ├── SkeletonLoader.vue         #   骨架屏
│   │   └── Toast.vue                  #   提示组件
│   ├── views/                         #   各标签页
│   │   ├── Dashboard.vue              #   概览仪表盘（默认首页）
│   │   ├── Reports.vue                #   日报历史
│   │   ├── Logs.vue                   #   运行日志 + 实时日志流
│   │   ├── Config.vue                 #   配置查看/编辑
│   │   ├── Stats.vue                  #   数据统计
│   │   ├── Camouflage.vue             #   伪装素材
│   │   ├── Sources.vue                #   采集源
│   │   └── Scheduler.vue              #   定时任务
│   └── styles/
│       └── main.css                   #   全局样式（Token Monitor 风格）
├── index.html                         # [新增] Vite 入口 HTML
├── package.json                       # [新增] Node.js 依赖
├── tsconfig.json                      # [新增] TypeScript 配置
├── serve.py                           # [新增] 纯 Web 服务模式入口
│
└── [现有文件均保持不变]
```

---

## 分阶段实施计划

### 阶段 0：后端拆分 — `serve.py` + 新增 API

**目标：** 把 Web 服务器从 `main.py` 剥离，新增桌面版需要的 API，确保 Python 后端可以独立启动。

**关键路径：** 此阶段是后续所有阶段的前置依赖。

---

### Task 0.1: 创建 `serve.py`

**Files:**
- Create: `serve.py`
- Modify: 无

创建纯 Web 服务模式的入口文件，不执行日报逻辑，只启动 FastAPI + 管理面板。

```python
"""
serve.py — DailyBot 后端服务（纯 Web 模式）
用法:
    python serve.py              # 启动服务（默认 8001 端口）
    python serve.py --port 9001  # 指定端口
"""
import asyncio
import sys
import uvicorn
from loguru import logger
from common import config
from oauth import oauth_platform_manager
from web import admin_router


def create_app():
    app = oauth_platform_manager.app
    app.include_router(admin_router, prefix="")
    return app


def main():
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8001
    host = "127.0.0.1"  # Electron 子进程只需本地访问
    
    logger.info(f"🚀 DailyBot 后端服务启动于 http://{host}:{port}")
    uvicorn.run(create_app(), host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
```

- [ ] **Step 1: 创建 `serve.py`**
- [ ] **Step 2: 验证可启动**

Run: `python serve.py`
Expected: 服务启动于 `http://127.0.0.1:8001`，访问 `/admin/status` 返回 JSON

- [ ] **Step 3: 提交**

```bash
git add serve.py
git commit -m "[feat] 新增 serve.py 纯 Web 服务模式入口"
```

---

### Task 0.2: 新增桌面版需要的 API

**Files:**
- Modify: `web/routes.py`

在现有路由中增加三个桌面版特有的端点：

```python
import asyncio
import json
import signal
from fastapi.responses import StreamingResponse


@router.get("/live-logs")
async def stream_live_logs():
    """SSE 实时日志流，用于桌面版执行日报时展示实时输出"""
    async def event_generator():
        # 从 loguru 的日志队列中读取并推送
        # 实现方式：将日志通过 Queue 转发给 SSE
        queue = asyncio.Queue()
        # ... 注册 loguru sink 到 queue
        try:
            while True:
                log_entry = await queue.get()
                yield f"data: {json.dumps(log_entry, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            pass
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/desktop-version")
async def check_version():
    """检查当前版本和最新版本（供桌面版更新提示用）"""
    import requests
    current = getattr(config, "VERSION", "1.1.2")
    latest = current
    download_url = ""
    try:
        resp = requests.get(
            "https://api.github.com/repos/你的用户名/daily-bot/releases/latest",
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            latest = data.get("tag_name", "").lstrip("v") or current
            download_url = data.get("html_url", "")
    except Exception:
        pass
    return {"current_version": current, "latest_version": latest, "has_update": latest != current, "download_url": download_url}


@router.post("/exit")
async def shutdown_backend():
    """关闭后端服务（桌面版退出时调用）"""
    async def _shutdown():
        await asyncio.sleep(0.5)
        os.kill(os.getpid(), signal.SIGINT)
    asyncio.create_task(_shutdown())
    return {"message": "服务即将关闭"}
```

- [ ] **Step 1: 在 `web/routes.py` 新增上述三个端点**

- [ ] **Step 2: 验证新 API**

Run: `python serve.py`（另一个终端）→ `curl http://127.0.0.1:8001/admin/desktop-version`
Expected: 返回版本信息 JSON

- [ ] **Step 3: 提交**

```bash
git add web/routes.py
git commit -m "[feat] 新增桌面版 API：live-logs / desktop-version / exit"
```

---

### 阶段 1：Vue 3 前端

**目标：** 用 Vue 3 + TypeScript + electron-vite 模板创建前端项目，完整复刻并增强现有管理面板。

**前置依赖：** 阶段 0 完成（后端 API 就绪可测试）。

---

### Task 1.1: 初始化 Vue 3 项目

**Files:**
- Modify: 项目根目录新增 `package.json` `tsconfig.json` `index.html` `src/` 等

```bash
cd D:/daily-bot
npm create @quick-start/electron@latest desktop-app -- --template vue-ts
```

注：`electron-vite` 官方脚手架会生成标准模板。我们将模板中的 `src/` 内容替换为自己的 Vue 组件，将 `electron/` 保留并定制。

关键依赖（在已有 `package.json` 基础上确保包含）：
- vue-router（路由管理）
- echarts + vue-echarts（统计图表）
- @vueuse/core（工具库，含系统通知、网络状态等）

- [ ] **Step 1: 运行脚手架并移入项目根目录**

脚手架生成 `desktop-app/` 目录，将 `electron/` `src/` `index.html` `package.json` `tsconfig.json` 等内容移入项目根目录，删除多余的 `desktop-app/` 外层目录。

Run:
```bash
cd D:/daily-bot
npm create @quick-start/electron@latest desktop-app -- --template vue-ts
# 将生成的文件移入项目根目录
```

- [ ] **Step 2: 安装额外依赖**

```bash
npm install vue-router@4 echarts vue-echarts @vueuse/core
npm install -D @types/node
```

- [ ] **Step 3: 验证能启动**

```bash
npm run dev
```
Expected: Electron 窗口弹出，显示默认模板页面。**关闭窗口，继续开发。**

---

### Task 1.2: 实现 API 客户端层

**Files:**
- Create: `src/api/client.ts`

```typescript
// src/api/client.ts — 封装所有后端 API 调用
const BASE = 'http://127.0.0.1:8001'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Accept': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`请求失败 ${res.status}: ${text.slice(0, 200)}`)
  }
  return res.json()
}

export interface SystemStatus {
  version: string
  enabled_workflows: string[]
  platforms: { name: string; ai_model: string; rpa_enabled: boolean }[]
  time: string
}

export interface Report {
  id: number
  date: string
  platform: string
  summary: string
  raw_data: string
  is_camouflage: number
  created_at: string
}

export interface RunLog {
  id: number
  date: string
  platform: string
  status: string
  message: string
  created_at: string
}

export interface TrendData {
  days: string[]
  counts: number[]
}

export interface PlatformStat {
  name: string
  success: number
  failed: number
  no_data: number
}

export interface CamouflageItem {
  id: string
  source_name: string
  content_preview: string
  platform: string
  last_used: string
  variants_count: number
}

export interface SourceInfo {
  platform: string
  enabled: boolean
  repo_count: number
  repos: { path: string; branch: string }[]
}

export const api = {
  getStatus: () => request<SystemStatus>('/admin/status'),
  getConfig: () => request<any>('/admin/config?masked=true'),
  getReports: (date?: string, platform?: string) => {
    let path = '/admin/reports?limit=50'
    if (date) path += `&date=${date}`
    if (platform) path += `&platform=${platform}`
    return request<{ date: string; reports: Report[]; count: number }>(path)
  },
  getReportDetail: (id: number) => request<{ report: Report }>(`/admin/reports/detail?id=${id}`),
  getLogs: (limit = 100) => request<{ logs: RunLog[]; count: number }>(`/admin/logs?limit=${limit}`),
  triggerReport: () => request<{ message: string; status: string }>('/admin/trigger', { method: 'POST' }),
  getTrend: (days = 7) => request<TrendData>(`/admin/stats/trend?days=${days}`),
  getPlatformStats: () => request<{ platforms: PlatformStat[] }>('/admin/stats/platform'),
  getCamouflage: () => request<{ items: CamouflageItem[] }>('/admin/camouflage'),
  deleteCamouflage: (id: string) => request<{ success: boolean }>(`/admin/camouflage/${id}`, { method: 'DELETE' }),
  getSources: () => request<{ sources: SourceInfo[] }>('/admin/sources'),
  addSource: (platform: string, repoPath: string, branch: string) =>
    request<{ success: boolean }>('/admin/sources', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform, repo_path: repoPath, branch }),
    }),
  deleteSource: (platform: string, index: number) =>
    request<{ success: boolean }>(`/admin/sources/${platform}/${index}`, { method: 'DELETE' }),
  getScheduler: () => request<{ config: any; installed_tasks: string[] }>('/admin/scheduler'),
  installScheduler: (time: string, weekdays?: number[]) =>
    request<{ success: boolean }>('/admin/scheduler/install', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ time, weekdays }),
    }),
  uninstallScheduler: () => request<{ success: boolean }>('/admin/scheduler/uninstall', { method: 'POST' }),
  getDesktopVersion: () => request<{ current_version: string; latest_version: string; has_update: boolean; download_url: string }>('/admin/desktop-version'),
}
```

- [ ] **Step 1: 创建 `src/api/client.ts`**

---

### Task 1.3: 实现全局样式（Token Monitor 风格）

**Files:**
- Create: `src/styles/main.css`

```css
/* src/styles/main.css — 深色玻璃拟态风格，参考 Token Monitor */
:root {
  /* 基底 */
  --bg-base: #303438;
  --bg-card: rgba(24, 28, 36, 0.8);
  --bg-card-hover: rgba(24, 28, 36, 0.9);
  
  /* 文字 */
  --text-primary: #eef5fb;
  --text-secondary: #a3adbb;
  --text-dim: rgba(163, 173, 187, 0.6);
  
  /* 强调色 */
  --accent: #b7ead4;
  --accent-hover: #8fdfbe;
  
  /* 状态语义 */
  --success: #4ec77f;
  --danger: #f06a7b;
  --warning: #f0a06a;
  --info: #6ab0f0;
  
  /* 玻璃效果 */
  --glass-bg: rgba(24, 28, 36, 0.75);
  --glass-border: rgba(128, 138, 152, 0.15);
  --glass-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
  --glass-blur: blur(32px);
  
  /* 间距（8px 网格） */
  --space-1: 8px;
  --space-2: 16px;
  --space-3: 24px;
  --space-4: 32px;
  
  /* 圆角 */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  
  /* 字体 */
  --font-mono: ui-monospace, 'Cascadia Code', 'Fira Code', 'Source Code Pro', Menlo, Consolas, monospace;
  --font-sans: -apple-system, 'Microsoft YaHei', 'PingFang SC', sans-serif;
  
  /* 过渡 */
  --transition-fast: 0.15s ease;
  --transition-slow: 0.2s ease;
  
  /* 滚动条 */
  --scrollbar-width: 6px;
  --scrollbar-bg: transparent;
  --scrollbar-thumb: rgba(128, 138, 152, 0.2);
  --scrollbar-thumb-hover: rgba(128, 138, 152, 0.35);
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: var(--font-mono);
  background: var(--bg-base);
  color: var(--text-primary);
  font-size: 12px;
  line-height: 1.6;
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
}

/* 滚动条 */
::-webkit-scrollbar { width: var(--scrollbar-width); }
::-webkit-scrollbar-track { background: var(--scrollbar-bg); }
::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--scrollbar-thumb-hover); }

/* 玻璃卡片 */
.glass-card {
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  box-shadow: var(--glass-shadow);
  transition: var(--transition-fast);
}
.glass-card:hover {
  border-color: rgba(128, 138, 152, 0.25);
}

/* 输入控件 */
input, select, textarea {
  font-family: var(--font-mono);
  font-size: 12px;
  background: rgba(24, 28, 36, 0.6);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  padding: 6px 10px;
  outline: none;
  transition: var(--transition-fast);
}
input:focus, select:focus, textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(183, 234, 212, 0.1);
}

/* 按钮 */
.btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px; border: none; border-radius: var(--radius-sm);
  font-family: var(--font-mono); font-size: 12px; font-weight: 500;
  cursor: pointer; transition: var(--transition-fast);
}
.btn-primary { background: var(--accent); color: #1a1e24; }
.btn-primary:hover { background: var(--accent-hover); }
.btn-ghost { background: rgba(255,255,255,0.06); color: var(--text-primary); border: 1px solid var(--glass-border); }
.btn-ghost:hover { background: rgba(255,255,255,0.1); }
.btn-danger { background: rgba(240, 106, 123, 0.15); color: var(--danger); border: 1px solid rgba(240, 106, 123, 0.2); }
.btn-danger:hover { background: rgba(240, 106, 123, 0.25); }

/* 标签 */
.tag {
  display: inline-block; padding: 2px 8px; border-radius: 12px;
  font-size: 11px; font-weight: 500;
}
.tag-success { background: rgba(78, 199, 127, 0.15); color: var(--success); }
.tag-danger  { background: rgba(240, 106, 123, 0.15); color: var(--danger); }
.tag-warning { background: rgba(240, 160, 106, 0.15); color: var(--warning); }
.tag-info    { background: rgba(106, 176, 240, 0.15); color: var(--info); }
.tag-accent  { background: rgba(183, 234, 212, 0.15); color: var(--accent); }
```

- [ ] **Step 1: 创建 `src/styles/main.css`**

---

### Task 1.4: 实现布局框架 + 路由

**Files:**
- Create: `src/App.vue`
- Create: `src/main.ts`

```vue
<!-- src/App.vue — 主布局：侧边栏导航 + 内容区 -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from './api/client'

const currentTab = ref('dashboard')
const systemStatus = ref<any>(null)
const showUpdateBadge = ref(false)

const tabs = [
  { key: 'dashboard', label: '概览', icon: '◉' },
  { key: 'reports', label: '日报', icon: '≡' },
  { key: 'logs', label: '日志', icon: '≫' },
  { key: 'config', label: '配置', icon: '⚙' },
  { key: 'stats', label: '统计', icon: '◈' },
  { key: 'camouflage', label: '伪装', icon: '◎' },
  { key: 'sources', label: '采集源', icon: '↗' },
  { key: 'scheduler', label: '定时', icon: '◷' },
]

function switchTab(key: string) { currentTab.value = key }

onMounted(async () => {
  try {
    systemStatus.value = await api.getStatus()
    const v = await api.getDesktopVersion()
    showUpdateBadge.value = v.has_update
  } catch {}
})
</script>

<template>
  <div class="app-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar glass-card">
      <div class="sidebar-header">
        <div class="logo">奕</div>
        <div class="version">{{ systemStatus?.version || '--' }}</div>
      </div>
      <nav class="sidebar-nav">
        <button v-for="tab in tabs" :key="tab.key"
                :class="['nav-item', { active: currentTab === tab.key }]"
                @click="switchTab(tab.key)">
          <span class="nav-icon">{{ tab.icon }}</span>
          <span class="nav-label">{{ tab.label }}</span>
          <span v-if="tab.key === 'config' && showUpdateBadge" class="update-dot"></span>
        </button>
      </nav>
      <div class="sidebar-footer">
        <div class="status-indicator" :class="systemStatus ? 'online' : 'offline'"></div>
        <span>{{ systemStatus ? '服务运行中' : '未连接' }}</span>
      </div>
    </aside>

    <!-- 内容区 -->
    <main class="main-content">
      <!-- 此处用 v-if 切换各视图组件 -->
      <Dashboard v-if="currentTab === 'dashboard'" />
      <Reports v-else-if="currentTab === 'reports'" />
      <Logs v-else-if="currentTab === 'logs'" />
      <Config v-else-if="currentTab === 'config'" />
      <Stats v-else-if="currentTab === 'stats'" />
      <Camouflage v-else-if="currentTab === 'camouflage'" />
      <Sources v-else-if="currentTab === 'sources'" />
      <Scheduler v-else-if="currentTab === 'scheduler'" />
    </main>
  </div>
</template>

<style scoped>
.app-layout { display: flex; height: 100vh; overflow: hidden; }
.sidebar { width: 180px; margin: var(--space-1); padding: var(--space-2); display: flex; flex-direction: column; border-radius: var(--radius-lg); flex-shrink: 0; }
.sidebar-header { text-align: center; padding-bottom: var(--space-2); border-bottom: 1px solid var(--glass-border); margin-bottom: var(--space-2); }
.logo { font-size: 28px; font-weight: 700; color: var(--accent); }
.version { font-size: 11px; color: var(--text-dim); margin-top: 4px; }
.sidebar-nav { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.nav-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; border: none; border-radius: var(--radius-sm); background: transparent; color: var(--text-secondary); cursor: pointer; font-family: var(--font-mono); font-size: 12px; transition: var(--transition-fast); text-align: left; width: 100%; }
.nav-item:hover { background: rgba(255,255,255,0.05); color: var(--text-primary); }
.nav-item.active { background: rgba(183, 234, 212, 0.1); color: var(--accent); }
.nav-icon { width: 16px; text-align: center; font-size: 13px; }
.update-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); margin-left: auto; }
.sidebar-footer { display: flex; align-items: center; gap: 8px; padding-top: var(--space-2); border-top: 1px solid var(--glass-border); font-size: 11px; color: var(--text-dim); }
.status-indicator { width: 8px; height: 8px; border-radius: 50%; }
.status-indicator.online { background: var(--success); box-shadow: 0 0 6px rgba(78,199,127,0.5); }
.status-indicator.offline { background: var(--danger); }
.main-content { flex: 1; overflow-y: auto; padding: var(--space-2); margin: var(--space-1) var(--space-1) var(--space-1) 0; }
</style>
```

```typescript
// src/main.ts
import { createApp } from 'vue'
import App from './App.vue'
import './styles/main.css'

createApp(App).mount('#app')
```

- [ ] **Step 1: 创建 `src/main.ts`**
- [ ] **Step 2: 创建 `src/App.vue`**
- [ ] **Step 3: 验证布局**

Run: `npm run dev`（后端先 `python serve.py`）
Expected: 左侧边栏（概览/日报/日志...）+ 右侧内容区

---

### Task 1.5: 概览仪表盘 Dashboard.vue

**Files:**
- Create: `src/views/Dashboard.vue`

核心展示内容：
- 4 个状态卡片：版本、工作流数、AI 模型、运行状态
- 今日日报摘要（如果有的话）
- 上次执行时间和结果
- 一键触发按钮
- 版本更新提示（如有）

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, SystemStatus } from '../api/client'

const status = ref<SystemStatus | null>(null)
const loading = ref(true)
const versionInfo = ref<any>(null)

onMounted(async () => {
  try {
    status.value = await api.getStatus()
    versionInfo.value = await api.getDesktopVersion()
  } catch {}
  loading.value = false
})

async function trigger() {
  // 调用触发 API
  await api.triggerReport()
}
</script>

<template>
  <div class="dashboard">
    <div class="page-header">
      <h2>概览</h2>
      <button class="btn btn-primary" @click="trigger">▶ 执行日报</button>
    </div>

    <!-- 状态卡片网格 -->
    <div class="stats-grid">
      <div class="glass-card stat-card">
        <div class="stat-label">版本</div>
        <div class="stat-value">{{ status?.version || '--' }}</div>
      </div>
      <div class="glass-card stat-card">
        <div class="stat-label">工作流</div>
        <div class="stat-value">{{ status?.enabled_workflows?.join(', ') || '--' }}</div>
      </div>
      <div class="glass-card stat-card">
        <div class="stat-label">AI 模型</div>
        <div class="stat-value">{{ status?.platforms?.[0]?.ai_model || '--' }}</div>
      </div>
      <div class="glass-card stat-card">
        <div class="stat-label">状态</div>
        <div class="stat-value">
          <span class="tag" :class="status ? 'tag-success' : 'tag-danger'">
            {{ status ? '运行中' : '离线' }}
          </span>
        </div>
      </div>
    </div>

    <!-- 版本更新提示 -->
    <div v-if="versionInfo?.has_update" class="glass-card update-banner">
      ✨ 新版本 {{ versionInfo.latest_version }} 可用（当前 {{ versionInfo.current_version }}）
    </div>

    <!-- 最近日报摘要 -->
    <div class="glass-card" style="padding: 16px; margin-top: 16px;">
      <h3 style="margin-bottom: 12px; font-size: 13px; color: var(--text-secondary);">最近日报</h3>
      <div class="text-dim">日报历史将在此展示最近 7 天的概览</div>
    </div>
  </div>
</template>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-3); }
.page-header h2 { font-size: 16px; font-weight: 600; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: var(--space-2); }
.stat-card { padding: var(--space-2); }
.stat-label { font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
.stat-value { font-size: 18px; font-weight: 600; }
.update-banner { padding: 12px 16px; margin-top: var(--space-2); border-left: 3px solid var(--accent); font-size: 12px; }
</style>
```

- [ ] **Step 1: 创建 `src/views/Dashboard.vue`**

---

### Task 1.6-1.13: 其余 7 个标签页

每个标签页遵循相同的模式——从 `api/client.ts` 调用接口，用玻璃卡片组件展示数据。

**Reports.vue** — 日报列表 + 日期筛选 + 详情弹窗。直接复用现有 dashboard.html 中的表格逻辑，翻译为 Vue 组件。

**Logs.vue** — 运行日志列表 + SSE 实时日志流。关键新增：点击"执行"后，通过 EventSource 连接 `/admin/live-logs` 在界面内滚动显示实时日志。

**Config.vue** — 配置查看（现有只读）+ 配置编辑（新增）。编辑模式下发送 `POST /admin/config` 更新 YAML。

**Stats.vue** — ECharts 图表（日报趋势柱状图 + 平台运行饼图）。

**Camouflage.vue** — 伪装素材表格 + 删除操作。

**Sources.vue** — 采集源管理列表 + 添加/删除表单。

**Scheduler.vue** — 定时任务状态 + 安装/卸载操作。

- [ ] **Step 1: 创建 `src/views/Reports.vue`**
- [ ] **Step 2: 创建 `src/views/Logs.vue`**
- [ ] **Step 3: 创建 `src/views/Config.vue`**
- [ ] **Step 4: 创建 `src/views/Stats.vue`**
- [ ] **Step 5: 创建 `src/views/Camouflage.vue`**
- [ ] **Step 6: 创建 `src/views/Sources.vue`**
- [ ] **Step 7: 创建 `src/views/Scheduler.vue`**

---

### Task 1.14: 配置编辑 API 补充

**Files:**
- Modify: `web/routes.py`

当前配置查看是 `GET /admin/config`，需新增配置更新端点：

```python
@router.post("/config")
async def update_config(data: dict):
    """更新配置（桌面版配置编辑用）"""
    try:
        # 验证数据为合法的 YAML 结构
        # 写入 config.yaml
        _write_config_yaml(data)
        # 重新加载配置
        config.reload()
        return {"success": True, "message": "配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 1: 在 `web/routes.py` 添加配置更新端点**

---

### 阶段 2：Electron 集成

**目标：** 定制 Electron 主进程，实现子进程管理 + 系统托盘 + 窗口生命周期。

**前置依赖：** 阶段 0 + 阶段 1 完成（后端 API 和 Vue 前端都已完成）。

---

### Task 2.1: 定制 Electron 主进程

**Files:**
- Modify: `electron/main/index.ts`

```typescript
import { app, BrowserWindow, shell } from 'electron'
import { spawn, ChildProcess } from 'child_process'
import path from 'path'
import { createTray } from './tray'

let mainWindow: BrowserWindow | null = null
let pythonProcess: ChildProcess | null = null

const PYTHON_PORT = 8001

function startPythonBackend() {
  // 优先使用打包后的 exe，否则用源码
  const isDev = !app.isPackaged
  const pythonCmd = isDev ? 'python' : path.join(process.resourcesPath, 'backend', 'dailybot-backend.exe')
  const args = isDev ? ['serve.py', '--port', String(PYTHON_PORT)] : ['--port', String(PYTHON_PORT)]
  
  pythonProcess = spawn(pythonCmd, args, {
    cwd: isDev ? app.getAppPath() : process.resourcesPath,
    stdio: ['pipe', 'pipe', 'pipe'],
  })
  
  pythonProcess.stdout?.on('data', (data) => {
    console.log(`[Python] ${data}`)
  })
  
  pythonProcess.on('exit', (code) => {
    console.log(`[Python] 进程退出 (code: ${code})`)
  })
}

function stopPythonBackend() {
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    frame: false,            // 无边框（使用自定义标题栏）
    transparent: true,       // 透明背景（玻璃效果）
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  // 开发模式加载 Vite 开发服务器，生产模式加载打包后的文件
  if (process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'))
  }

  // 点击关闭按钮时隐藏到托盘，不退出
  mainWindow.on('close', (event) => {
    if (!app.isQuitting) {
      event.preventDefault()
      mainWindow?.hide()
    }
  })
}

app.whenReady().then(() => {
  startPythonBackend()
  createWindow()
  createTray(mainWindow)
})

app.on('window-all-closed', () => {
  // 不退出，托盘还在
})

app.on('before-quit', () => {
  app.isQuitting = true
  stopPythonBackend()
})
```

- [ ] **Step 1: 写入 `electron/main/index.ts`**

---

### Task 2.2: 系统托盘

**Files:**
- Create: `electron/main/tray.ts`

```typescript
import { app, Menu, Tray, BrowserWindow, nativeImage, Notification } from 'electron'
import path from 'path'

let tray: Tray | null = null

export function createTray(mainWindow: BrowserWindow | null) {
  const iconPath = path.join(__dirname, '../../resources/icon.png')
  tray = new Tray(nativeImage.createFromPath(iconPath))
  
  const contextMenu = Menu.buildFromTemplate([
    {
      label: '打开 DailyBot',
      click: () => {
        mainWindow?.show()
        mainWindow?.focus()
      },
    },
    {
      label: '立即执行日报',
      click: async () => {
        // 通过 fetch 触发后端执行
        try {
          await fetch('http://127.0.0.1:8001/admin/trigger', { method: 'POST' })
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
  tray.setContextMenu(contextMenu)
  
  tray.on('double-click', () => {
    mainWindow?.show()
    mainWindow?.focus()
  })
}
```

- [ ] **Step 1: 创建 `electron/main/tray.ts`**

---

### Task 2.3: 系统通知 + 开机自启管理

**Files:**
- Modify: `electron/main/index.ts`

在 Electron 主进程中增加：
1. 日报执行完成时弹出系统通知（从后端推送结果）
2. 开机自启开关（通过 `app.setLoginItemSettings()`）

```typescript
// 在 main/index.ts 增加开机自启管理
export function setAutoLaunch(enabled: boolean) {
  app.setLoginItemSettings({
    openAtLogin: enabled,
    path: app.getPath('exe'),
  })
}
```

在 Vue 前端 `Scheduler.vue` 中增加开机自启开关按钮。

- [ ] **Step 1: 在主进程添加 `setAutoLaunch`**
- [ ] **Step 2: 在前端添加开机自启 UI 开关**

---

### Task 2.4: 实时日志的 SSE 流

**Files:**
- Create: `src/composables/useLiveLogs.ts`

```typescript
import { ref, onUnmounted } from 'vue'

export function useLiveLogs() {
  const logs = ref<string[]>([])
  const isConnected = ref(false)
  let eventSource: EventSource | null = null

  function connect() {
    logs.value = []
    eventSource = new EventSource('http://127.0.0.1:8001/admin/live-logs')
    isConnected.value = true

    eventSource.onmessage = (event) => {
      logs.value.push(event.data)
    }

    eventSource.onerror = () => {
      isConnected.value = false
    }
  }

  function disconnect() {
    eventSource?.close()
    isConnected.value = false
  }

  onUnmounted(() => disconnect())

  return { logs, isConnected, connect, disconnect }
}
```

- [ ] **Step 1: 创建 `src/composables/useLiveLogs.ts`**

---

### 阶段 3：打包

**目标：** 将 Python 后端打包为 exe，Electron 打包为安装包，二者合一。

---

### Task 3.1: Python 后端 PyInstaller 打包

**Files:**
- Modify: `scripts/build_backend.py` 或创建新的打包脚本

```bash
# 用 PyInstaller 打包 Python 后端
pyinstaller --onefile --name dailybot-backend ^
  --add-data "config/config.yaml;config" ^
  --add-data "prompts;prompts" ^
  --add-data "api;api" ^
  --add-data "common;common" ^
  --add-data "crawlers;crawlers" ^
  --add-data "enums;enums" ^
  --add-data "exceptions;exceptions" ^
  --add-data "oauth;oauth" ^
  --add-data "providers;providers" ^
  --add-data "request;request" ^
  --add-data "token_storage;token_storage" ^
  --add-data "utils;utils" ^
  --add-data "web;web" ^
  --add-data "workflows;workflows" ^
  --hidden-import "uvicorn.logging" ^
  serve.py
```

- [ ] **Step 1: 创建打包脚本并运行**
- [ ] **Step 2: 验证打包后的 exe 可独立启动**

---

### Task 3.2: Electron Builder 打包

在 `package.json` 中配置 electron-builder：

```json
{
  "build": {
    "appId": "com.dailybot.app",
    "productName": "DailyBot",
    "directories": { "output": "release" },
    "extraResources": [
      { "from": "dist-backend/dailybot-backend.exe", "to": "backend/dailybot-backend.exe" }
    ],
    "win": {
      "target": ["nsis"],
      "icon": "resources/icon.ico"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true
    }
  }
}
```

```bash
# 构建前端 + 打包 Electron
npm run build
```

- [ ] **Step 1: 配置 electron-builder**
- [ ] **Step 2: 完整打包验证**

---

## API 接口清单

### 现有接口（全部复用）

| 接口 | 方法 | 用途 |
|------|------|------|
| `/admin/status` | GET | 系统状态 |
| `/admin/config` | GET | 配置查看（脱敏） |
| `/admin/reports` | GET | 日报列表 |
| `/admin/reports/detail` | GET | 日报详情 |
| `/admin/logs` | GET | 运行日志 |
| `/admin/trigger` | GET/POST | 手动触发 |
| `/admin/stats/trend` | GET | 趋势数据 |
| `/admin/stats/platform` | GET | 平台统计 |
| `/admin/camouflage` | GET | 伪装素材列表 |
| `/admin/camouflage/{id}` | DELETE | 删除素材 |
| `/admin/sources` | GET/POST | 采集源管理 |
| `/admin/sources/{p}/{i}` | DELETE | 删除采集源 |
| `/admin/scheduler` | GET | 调度器状态 |
| `/admin/scheduler/install` | POST | 安装定时任务 |
| `/admin/scheduler/uninstall` | POST | 卸载定时任务 |

### 新增接口

| 接口 | 方法 | 用途 | 所属阶段 |
|------|------|------|---------|
| `/admin/live-logs` | GET | SSE 实时日志流 | 阶段 0 |
| `/admin/desktop-version` | GET | 版本更新检查 | 阶段 0 |
| `/admin/config` | POST | 配置编辑保存 | 阶段 1 |
| `/admin/exit` | POST | 关闭后端服务 | 阶段 0 |

---

## 预计工作量

| 阶段 | 任务数 | 预计耗时 | 依赖 |
|------|--------|---------|------|
| 阶段 0：后端拆分 | 2 个 Task | 1 天 | 无 |
| 阶段 1：Vue 3 前端 | 14 个 Task | 3-4 天 | 阶段 0 |
| 阶段 2：Electron 集成 | 4 个 Task | 1-2 天 | 阶段 0 + 1 |
| 阶段 3：打包 | 2 个 Task | 1 天 | 全部完成 |
| **总计** | **22 个 Task** | **5-8 天** | - |

---

## 关键路径

```
阶段 0: serve.py ───────────────────────────────┐
                                                ├──▶ 阶段 2: Electron 集成 ──▶ 阶段 3: 打包
阶段 0: 新增 API ───▶ 阶段 1: Vue 3 前端 ──────┘
```

阶段 0 和阶段 1 可以部分并行——后端拆分完成后即可开始 Vue 开发（无需等全部 API 就绪，可以用 mock 数据）。
