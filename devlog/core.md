# core 模块日志

## 2026-06-24 15:00: 提取核心报告引擎
- **文件:**
  - `core/__init__.py`
  - `core/engine.py`
- **原因:** 将主流程逻辑从 `main.py` 提取到独立模块，避免 Web 面板手动触发时出现 `__main__` 模块导入问题
- **决策:** 创建 `core/engine.py` 包含 `run_reporting_logic()`、`ensure_playwright_browsers()`、`trigger_rpa()`，`main.py` 改为从 `core.engine` 导入
- **影响范围:** `main.py` 精简 ~300 行，`web/routes.py` 可直接导入 `run_reporting_logic`

## 2026-06-26: 修复 Database.save_report 参数名错误
- **文件:**
  - `core/engine.py`
- **原因:** `finalize_workflow_async` 调用 `db.save_report()` 时使用了 `raw_report=` 参数，但方法签名定义为 `raw_data`。调用时抛出 `TypeError`。
- **决策:** 将 `raw_report=` 改为 `raw_data=`
- **影响范围:** 日报推送成功后数据库写入环节
