# config 模块日志

## 2026-06-26: 切换 ocgt 代理到 openai 直连模式
- **文件:**
  - `config/config.yaml`
- **原因:** ocgt 代理返回 401 (invalid auth token)，改用 openai 兼容 API 直连
- **决策:** 
  - `platforms.feishu.ai_model`: `anthropic` → `openai`
  - `models.openai.base_url`: `https://opencode.ai/zen/go/v1`
  - `models.openai.models`: `["deepseek-v4-flash"]`
  - `.env` 新增 `OPENAI_API_KEY`（gitignored）
- **影响范围:** AI 总结请求走 openai 兼容格式，不再依赖 ocgt 代理

## 2026-07-01: 移除 config.yaml 中硬编码的 API Key
- **文件:**
  - `config/config.yaml`
- **原因:** 安全审查发现 OpenAI API Key 硬编码在 YAML 中并已提交到 git 历史
- **决策:** 将 `models.openai.api_key` 置空，Key 已通过 `.env` 的 `OPENAI_API_KEY` 加载（优先级高于 YAML）
- **影响范围:** `config/config.yaml`