# providers 模块日志

## 2026-06-28: AIFactory 新增通用 chat 方法
- **文件:**
  - `providers/modules/ai_factory.py`
- **原因:** AI 对话查询功能需要通用对话接口，现有 `summarize` 方法绑定日报提示词模板
- **决策:** 新增 `chat(question, system_prompt)` 方法，构造轻量 messages payload，复用现有 `chat_req.fetch` 和 `_parse_response`
- **影响范围:** AIFactory 新增 1 个公共方法，不影响现有 summarize 逻辑

## 2026-06-26: 修复 AI Provider API 调用链路
- **文件:**
  - `providers/impl/anthropic_ai.py`
  - `providers/impl/ollama_ai.py`
- **原因:** AI Provider 使用 `self.api(...)` 直接调用 `use_request` 返回的 `DotDict`，但 `DotDict` 未实现 `__call__`，每次调用都会抛出 `TypeError`（此前因采集 0 条数据引擎提前返回，从未触发到此路径）
- **决策:** 移除 `use_request`/`apis` 依赖，改为直接使用 `httpx.AsyncClient(verify=False)` 调用 API
- **影响范围:** AnthropicAI.summarize()、OllamaAI.summarize()

## 2026-06-26: AI Provider 添加 HTTP 状态码检查
- **文件:**
  - `providers/impl/anthropic_ai.py`
  - `providers/impl/ollama_ai.py`
- **原因:** 直接调用 `resp.json()` 前未检查 `resp.status_code`，4xx/5xx 错误被静默处理为"无内容返回"
- **决策:** 在 `resp.json()` 前添加状态码检查，非 200 时记录错误日志并显式返回错误信息
- **影响范围:** AnthropicAI.summarize()、OllamaAI.summarize()
