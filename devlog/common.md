# common 模块日志

## 2026-06-24: 新增统计与查询方法
- **文件:**
  - `common/database.py`
- **原因:** 后端 API 增强需要数据库层新增 3 个方法
- **决策:**
  - `get_report_trend(days)` — 按日期统计日报提交趋势
  - `get_platform_stats()` — 按平台+状态统计运行日志
  - `get_report_by_id(report_id)` — 按 ID 查询单条日报详情
- **影响范围:** 新增 3 个 Database 方法，供 web 路由层调用

## 2026-06-26: 修复 Windows 终端编码问题
- **文件:**
  - `common/logger.py`
- **原因:** Windows 控制台 GBK 编码无法输出 emoji，导致 loguru 写入 stdout 时 UnicodeEncodeError 崩溃
- **决策:** 在日志初始化前对 sys.stdout/stderr 执行 reconfigure(encoding="utf-8", errors="replace")
- **影响范围:** 所有终端日志输出
