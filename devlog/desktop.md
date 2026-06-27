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

## 2026-06-27: Sprint 1 — 日常体验提升（窗口持久化/托盘/快捷键/自检）
- **文件:**
  - `desktop/electron/main/index.ts`
  - `desktop/src/App.vue`
  - `desktop/src/views/Dashboard.vue`
- **原因:** 桌面版功能基本完成后，需要优化日常使用体验
- **决策:**
  - 窗口位置/大小持久化：关闭时自动保存 bounds 到 `userData/window-state.json`，启动时恢复
  - 开机自启到托盘：检测 `wasOpenedAtLogin`，自启时不弹窗口只驻留托盘
  - 全局快捷键：`Ctrl+Alt+D` 呼出/隐藏窗口
  - 键盘导航：数字键 1-8 切换页面，`Ctrl+E` 快速执行日报
  - 环境自检：Dashboard 加载时检测配置完整性，显示缺失警告 banner
- **影响范围:** Electron 主进程、App 布局、Dashboard 概览页

## 2026-06-27: Sprint 2 — 数据能力增强（搜索/导出/聚合/对比/通知）
- **文件:**
  - `common/database.py`
  - `web/routes.py`
  - `desktop/src/api/client.ts`
  - `desktop/src/views/Reports.vue`
  - `desktop/src/views/Logs.vue`
  - `desktop/src/views/Stats.vue`
  - `desktop/src/views/Dashboard.vue`
  - `desktop/electron/main/index.ts`
  - `desktop/electron/preload/index.ts`
  - `desktop/src/vite-env.d.ts`
- **原因:** 桌面版功能基本完成后，需要增强数据处理能力和使用体验
- **决策:**
  - 搜索增强：后端 reports/logs API 增加 search 参数做 LIKE 模糊匹配，前端增加搜索输入框
  - CSV 导出：Reports 页面增加"导出 CSV"按钮，客户端生成 UTF-8 BOM CSV 下载
  - 周报/月报：后端新增 `/admin/reports/summary` 聚合接口 + Stats.vue 增加汇总统计面板
  - 多平台对比：后端新增 `get_platform_trend` 方法 + 路由 + Stats.vue 堆叠柱状图
  - 系统通知：Dashboard 触发日报后通过 SSE 监听执行进度，完成时发原生通知 + Toast
- **影响范围:** 后端 2 文件 + 前端 6 文件

## 2026-06-27: 审查修复 — SSE 鉴权/窗口事件/内存泄漏/冗余导入
- **文件:**
  - `desktop/src/views/Dashboard.vue`
  - `desktop/electron/main/index.ts`
  - `desktop/src/views/Stats.vue`
  - `desktop/src/views/Reports.vue`
- **原因:** 全面审查修改完整性时发现的问题
- **决策:**
  - SSE 鉴权：EventSource 不支持自定义 Header，硬编码 key 有安全隐患；改用 fetch + ReadableStream 读取 SSE 流，走 `X-Desktop-Client` 头
  - 窗口事件：重复的 `win.on('close')` 合并为一个；resize/move 保存防抖 500ms 避免频繁写磁盘
  - 内存泄漏：Reports.vue 的 keydown 监听器缺少 `onBeforeUnmount` 清理
  - 冗余导入：Stats.vue 的 `computed` 导入了但未使用
- **影响范围:** 前端 3 文件 + Electron 主进程 1 文件

## 2026-06-27: Sprint 3 — 数据归档与清理
- **文件:**
  - `common/database.py`
  - `web/routes.py`
  - `desktop/src/api/client.ts`
  - `desktop/src/views/Scheduler.vue`
- **原因:** 数据库无限增长需要清理策略
- **决策:**
  - 后端新增 `cleanup_old_records(days)` 方法，支持按天数清理日报/日志/伪装历史
  - 后端新增 `POST /admin/maintenance/cleanup` 接口
  - 前端 Scheduler 页面增加"数据维护"卡片，可选 7/30/90/180 天保留策略
- **影响范围:** 后端 2 文件 + 前端 2 文件
