# desktop 模块日志

## 2026-06-27: 审查修复 — API key 硬编码 + 健康检查 + 类型声明
- **文件:**
  - `desktop/src/api/client.ts`
  - `desktop/electron/main/index.ts`
  - `desktop/src/components/TitleBar.vue`
  - `desktop/src/vite-env.d.ts`
- **修复内容:**
  - 去掉 client.ts 中硬编码的 `key=dailybot-admin`，改用 `X-Desktop-Client` 头部
  - 后端 verify_admin_key 识别该头部后跳过本地鉴权
  - Electron 主进程启动后轮询 `/health` 确认后端就绪再创建窗口
  - 补充 TypeScript 类型声明，windowControls / electronAPI 挂载到 Window 接口

## 2026-06-27: 主题色选择 + 排版现代化
- **文件:**
  - `desktop/src/styles/main.css`
  - `desktop/src/components/ThemeSwitcher.vue`
  - `desktop/src/App.vue`
- **新增:**
  - 5 套主题色：薄荷（默认）、海洋、薰衣草、落日、玫瑰
  - ThemeSwitcher 组件：侧边栏底部主题切换面板，选择即时生效并保存 localStorage
  - 主题系统通过 `data-theme` 属性切换，深色背景色 + 强调色同步变化
  - 环境光晕颜色随主题联动
- **排版优化:**
  - 侧边栏改为品牌区（图标 + 名称 + 版本）+ 导航 + 底部操作区
  - 内容区 padding 加大，呼吸感更强
  - 按钮 active 缩放加强（0.96x）
  - 页面过渡动画调优

## 2026-06-27: 深度优化 — 毛玻璃质感 + 动效 + Toast 通知
- **文件:**
  - `desktop/src/styles/main.css`
  - `desktop/src/components/TitleBar.vue`
  - `desktop/src/components/Toast.vue`
  - `desktop/src/App.vue`
  - `desktop/src/views/Dashboard.vue`
  - `desktop/src/views/Logs.vue`
  - `desktop/src/views/Config.vue`
  - `desktop/src/views/Reports.vue`
  - `desktop/src/views/Sources.vue`
  - `desktop/src/views/Camouflage.vue`
  - `desktop/src/views/Scheduler.vue`
- **优化内容:**
  - 毛玻璃质感：环境光晕浮动球体、玻璃卡片内发光/边缘光泽、背景 acrylic 模糊叠加
  - SVG 图标按钮（最小化/最大化/关闭替换文本符号）
  - Toast 组件：玻璃风格通知提示，进入/退出动画，支持 success/error/info
  - 页面切换动画：Transition 组件实现淡入 + 位移
  - 日志列表 TransitionGroup 逐条渐入动画
  - 骨架屏 shimmer 动画替代 loading 文字
  - 状态卡片悬浮辉光效果
  - 侧边栏导航活跃指示器（左侧亮条）
  - 所有 alert() 替换为 Toast 通知
  - 按钮 active 缩放反馈（0.97x）

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
