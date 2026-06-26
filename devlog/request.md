# request 模块日志

## 2026-06-26: 修复 PlatformFactory api_key 读取未触发环境变量覆盖
- **文件:**
  - `request/platforms/modules/platform_factory.py`
- **原因:** `PlatformFactory.create` 使用 `model_cfg.get("api_key")` 读取 api_key，但 `config.get_model()` 返回的 dict 中，环境变量注入的 api_key 被 `_inject_env_value` 写入了错误的键路径（`API.KEY` 而非 `api_key`），导致 api_key 始终为空字符串，API 请求缺少 Authorization header 返回 "Missing API key"。
- **决策:** 改用 `config.get(f"models.{platform_name}.api_key", "")` 完整路径读取，此路径的 `path_to_attr_name` 正确生成 `OPENAI_API_KEY`，与环境变量精确匹配。
- **影响范围:** PlatformFactory 动态生成的所有平台实例（openai、anthropic 等）
- **踩坑:** `_inject_env_value` 在 `prefix_under` 模式下将 `remaining` 中的 `_` 替换为 `.`，导致单键名 `api_key` 被拆分为嵌套路径 `API.KEY`，无法匹配 YAML 原键。这是 Config 系统的潜在通用 bug。