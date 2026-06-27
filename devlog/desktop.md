# desktop 模块日志

## 2026-06-27: 窗口优化 — 无边框 + 自定义标题栏 + 透明背景
- **文件:**
  - `desktop/electron/main/index.ts`
  - `desktop/electron/preload/index.ts`
  - `desktop/src/components/TitleBar.vue`
  - `desktop/src/App.vue`
  - `desktop/src/styles/main.css`
  - `desktop/index.html`
- **原因:** 原生 Windows 标题栏与玻璃拟态风格不匹配
- **决策:** 
  - 启用 frame:false 无边框模式，配合 transparent + acrylic 毛玻璃效果
  - 自定义 TitleBar 组件：左侧应用图标/名称（可拖拽）、右侧最小化/最大化/关闭
  - preload 通过 contextBridge 暴露 windowControls API，确保安全性
  - 最大化/非最大化状态通过 IPC 实时同步到渲染进程
- **影响范围:** 桌面版窗口样式和交互方式

## 2026-06-27: 创建 Electron + Vue 3 桌面版项目骨架
- **文件:**
  - `desktop/package.json`
  - `desktop/electron/main/index.ts`
  - `desktop/src/main.ts`
  - `desktop/src/App.vue`
  - `desktop/src/api/client.ts`
  - `desktop/src/styles/main.css`
  - `desktop/src/views/Dashboard.vue`
  - `desktop/src/views/Reports.vue`
  - `desktop/src/views/Logs.vue`
  - `desktop/src/views/Config.vue`
  - `desktop/src/views/Stats.vue`
  - `desktop/src/views/Camouflage.vue`
  - `desktop/src/views/Sources.vue`
  - `desktop/src/views/Scheduler.vue`
- **原因:** 实现 ADR-0001，将管理面板从原生 HTML 迁移到 Electron + Vue 3 桌面应用
- **决策:**
  - 使用 electron-vite + Vue 3 + TypeScript 技术栈
  - Electron 主进程管理 Python 后端子进程（serve.py）和系统托盘
  - Vue 前端通过 REST API 与后端通信，Python 代码零改动
  - UI 风格采用深色玻璃拟态（参考 Token Monitor 风格体系）
- **影响范围:** 新增 desktop/ 独立子项目，不影响现有 Python 代码
