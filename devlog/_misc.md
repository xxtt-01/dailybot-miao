# 杂项日志

## 2026-06-24 15:00: main.py 提取引擎 + 管理面板自动启动
- **文件:**
  - `main.py`
- **原因:** 将核心逻辑提取到 `core/engine`，Web 面板手动触发时无需依赖 `__main__` 模块
- **决策:**
  - 移除 `json`/`sys`/`textwrap`/`crawler_manager`/`RPAFactory`/`camouflage_history_manager` 等已迁移的导入
  - 如果 `admin.api_key` 已配置，自动启动 Web 服务器（即使无 OAuth 需求）

## 2026-06-24 15:00: 使用说明更新可视化面板
- **文件:**
  - `使用说明.html`
- **原因:** 新增 FAQ 条目介绍 Web 管理面板的访问方式
