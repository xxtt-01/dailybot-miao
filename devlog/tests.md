# tests 模块日志

## 2026-06-24 15:00: 更新测试导入路径
- **文件:**
  - `tests/test_core_flow.py`
- **原因:** `ensure_playwright_browsers` 和 `run_reporting_logic` 从 `main.py` 迁移到 `core/engine.py`
- **决策:** 测试导入从 `from main import ...` 改为 `from core.engine import ...`
