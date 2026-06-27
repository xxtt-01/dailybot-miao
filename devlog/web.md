# web 模块日志

## 2026-06-27: 新增桌面版 API（live-logs / desktop-version / exit / config POST）
- **文件:**
  - `web/routes.py`
- **原因:** 桌面版（Electron）需要实时日志流、版本更新检查、服务关闭通知、配置在线编辑等专用端点
- **决策:** 新增 4 个 API，其中 live-logs 使用 SSE 推送机制 + loguru sink 捕获实时日志，exit 用异步延迟关闭
- **影响范围:** 桌面版前端可调用的 API 集合

## 2026-06-27: 修复 Dashboard "日报喵" 标题和图标残留
- **文件:**
  - `web/static/dashboard.html`
- **原因:** AI 角色已从"日报喵"重命名为"小奕"，但 Dashboard 仍显示旧名称和猫图标
- **决策:** 标题改为"小奕 DailyBot 管理面板"，Logo 从 🐱 改为 ✨
- **影响范围:** Web 管理面板标题栏

## 2026-06-24 15:00: 创建管理面板前端 + 手动触发接口
- **文件:**
  - `web/static/dashboard.html`
  - `web/routes.py`
- **原因:** 用户需要可视化前端面板，代替纯黑盒命令行运行
- **决策:**
  - 液态拟态毛玻璃（liquid glassmorphism）暗色主题 UI
  - 单页 HTML 内嵌 CSS/JS，零依赖
  - 4 个概览卡片 + 3 个 Tab（日报历史 / 运行日志 / 配置查看）
  - 新增 `GET|POST /admin/trigger` 手动触发日报
  - 前端通过 `?key=xxx` 鉴权调用现有 API
- **影响范围:** 新增 `web/static/dashboard.html`，`web/routes.py` 新增 trigger 端点

## 2026-06-24 18:55: 仪表盘新增 6 个功能（详情弹窗/图表/伪装/采集源/调度器/主题切换）
- **文件：**
  - `web/static/dashboard.html`
- **原因：** 管理面板需要更多功能 Tab 和交互能力
- **决策：**
  - 复用已有 glassmorphism 样式体系，新增 4 个功能 Tab
  - ECharts CDN 避免 npm 依赖，延迟初始化解决 display:none 渲染问题
  - 主题切换使用 CSS 变量覆盖 + localStorage 持久化
- **影响范围：** `dashboard.html` 从 705 行增至 1213 行
- **新增功能：**
  1. 日报详情弹窗 — 完整 summary + raw_data 格式化 JSON 展示
  2. 数据统计 — ECharts 柱状图 + 饼图，支持 7日/30日切换，响应式 resize
  3. 伪装素材管理 — 列表展示 + 确认删除
  4. 采集源管理 — 平台卡片 + 仓库增删表单
  5. 定时任务管理 — 状态卡片 + 安装/卸载操作
  6. 深色/浅色主题切换 — CSS 变量 + localStorage 持久化

## 2026-06-24: 新增 11 个 admin API 端点
- **文件:**
  - `web/routes.py`
- **原因:** 管理面板需要更多后端 API 支持统计、伪装素材管理、采集源管理、定时任务管理
- **决策:**
  - 新增 `_write_config_yaml` 辅助函数用于安全更新 YAML 配置
  - 新增 11 个端点覆盖 4 个功能域：
    - 数据统计：`GET /reports/detail`、`GET /stats/trend`、`GET /stats/platform`
    - 伪装素材：`GET/DELETE /camouflage`、`DELETE /camouflage/{item_id}`
    - 采集源管理：`GET/POST/DELETE /sources`
    - 定时任务：`GET /scheduler`、`POST /scheduler/install`、`POST /scheduler/uninstall`
- **依赖:** 依赖于 `common.database` 新增的 3 个方法和 `camouflage_history_manager` 新增的 2 个方法
- **影响范围:** `web/routes.py` 路由总数从 5 增至 16
