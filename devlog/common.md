# common 模块日志

## 2026-06-27: 修复 config.py env 注入下划线转点号 Bug
- **文件:**
  - `common/config.py`
- **原因:** `_inject_env_value` 中 `remaining.replace("_", ".")` 将 `API_KEY` 转为 `API.KEY`，导致注入时拆成嵌套路径 `["api"]["key"]` 而非单 key `api_key`
- **根因:** 下划线既可能是 key 名的组成部分（如 api_key），也可能是嵌套路径分隔符（如 params_timeout），原代码一刀切全转点号
- **决策:** 
  1. 去除 `prefix_under` 匹配分支的 `replace("_", ".")`，保持下划线原样传递
  2. 在 `_inject_env_value` 中增加启发式检测：单 key 含下划线且首段匹配现有 dict key 时，再拆分为嵌套路径递归处理
- **影响范围:** 所有通过下划线风格 env 变量注入的配置项（如 `OPENAI_API_KEY`、`CRAWLER_SOURCES.GITHUB.TOKEN` 等）
- **踩坑:** 无完美解决方案，只能通过启发式（首段 key 检查）做最佳近似

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
