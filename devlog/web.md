# web 模块日志

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
