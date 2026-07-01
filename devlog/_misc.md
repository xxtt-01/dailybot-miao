# 杂项日志

## 2026-06-27: pyproject.toml 补回 emoji
- **文件:**
  - `pyproject.toml`
- **原因:** 上次更新丢失了 emoji 符号
- **决策:** 补回 ✨，description 改为 "✨ 小奕 - AI 驱动的日报自动化工具"

## 2026-06-27: 新增 serve.py 纯 Web 服务模式入口
- **文件:**
  - `serve.py`
- **原因:** 桌面版（Electron）需要将 Python 后端作为子进程启动，现有的 main.py 执行完整日报流程不适合作为常驻服务
- **决策:** 新建 serve.py，只启动 FastAPI + 管理面板，不触发日报逻辑；由 Electron 主进程管理生命周期
- **影响范围:** Electron 桌面版的子进程启动方式

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

## 2026-07-01: .gitignore 添加运行时生成文件
- **文件:**
  - `.gitignore`
- **原因:** `token.json` 包含飞书 OAuth 敏感令牌，`camouflage_history.json` 是运行时数据文件，`nul` 是 Windows 重定向残留
- **决策:** 将 `token.json`、`camouflage_history.json`、`nul` 加入 .gitignore
- **影响范围:** `.gitignore`

## 2026-07-01: CI 手动触发 + 异常处理和 JSON 工具函数
- **文件:**
  - `.github/workflows/release.yml`
  - `exceptions/handler.py`
  - `utils/path_helper.py`
- **原因:** 
  - release.yml 缺少 `workflow_dispatch` 无法手动触发
  - exception handler 误拦截 HTTPException 导致 API 异常返回 500 而非正确状态码
  - 缺少 JSON 文件读写工具函数
- **决策:**
  - release.yml 增加 `workflow_dispatch:` 支持 GitHub Actions 手动触发
  - handler.py: `HTTPException` 直接 `raise` 透传，不进入全局异常处理
  - path_helper.py: 新增 `read_json()` 和 `write_json()` 工具函数（带目录自动创建）
- **影响范围:** `.github/workflows/release.yml`、`exceptions/handler.py`、`utils/path_helper.py`