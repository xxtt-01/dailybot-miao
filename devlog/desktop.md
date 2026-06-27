# desktop 模块日志

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
