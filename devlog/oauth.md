# oauth 模块日志

## 2026-06-27: 更新 FastAPI 标题 "日报喵" → "小奕"
- **文件:**
  - `oauth/modules/oauth_platform_manager.py`
- **原因:** AI 角色名统一更新
- **决策:** FastAPI title 改为 "DailyBot 小奕"
- **影响范围:** OAuth 服务器实例标题

## 2026-06-24 15:00: 注册根路由仪表盘
- **文件:**
  - `oauth/modules/oauth_platform_manager.py`
- **原因:** 需要提供 Web 管理面板入口
- **决策:**
  - `GET /` 返回 `web/static/dashboard.html`（FileResponse）
  - `GET /health` 健康检查端点
  - 使用 `include_in_schema=False` 避免污染 OpenAPI 文档
- **影响范围:** FastAPI 应用新增根路由

## 2026-07-01: 修复 CORS allow_credentials 与 allow_origins=["*"] 冲突
- **文件:**
  - `oauth/modules/oauth_platform_manager.py`
- **原因:** CORS 规范不允许 `allow_credentials=True` 与 `allow_origins=["*"]` 同时使用
- **决策:** `allow_credentials` 改为 `False`（开发模式无需凭据，生产 Electron 无跨域问题）
- **影响范围:** `oauth/modules/oauth_platform_manager.py`