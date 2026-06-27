# 杂项日志

## 2026-06-27: 更新 pyproject.toml 项目描述
- **文件:**
  - `pyproject.toml`
- **原因:** AI 角色名统一更新
- **决策:** description 改为 "小奕 - AI 驱动的日报自动化工具"
- **影响范围:** 项目元数据

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

## 2026-06-26: 修复 dailybot_scheduler 日志格式
- **文件:**
  - `dailybot_scheduler.py`
- **原因:** `setup_logging()` 返回标准 logging.Logger，但日志调用用了 loguru 的 `{}` 格式化语法，导致 TypeError
- **决策:** 将 `log.info("...{}...", arg)` 改为 `log.info("...%s...", arg)` 和 `log.info("...%d...", arg)`，兼容标准 logging
- **影响范围:** run.py 和定时任务触发的日志输出
