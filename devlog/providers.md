# providers 模块日志

## 2026-06-26: 修复 AI Provider API 调用链路
- **文件:**
  - `providers/impl/anthropic_ai.py`
  - `providers/impl/ollama_ai.py`
- **原因:** AI Provider 使用 `self.api(...)` 直接调用 `use_request` 返回的 `DotDict`，但 `DotDict` 未实现 `__call__`，每次调用都会抛出 `TypeError`（此前因采集 0 条数据引擎提前返回，从未触发到此路径）
- **决策:** 移除 `use_request`/`apis` 依赖，改为直接使用 `httpx.AsyncClient(verify=False)` 调用 API
- **影响范围:** AnthropicAI.summarize()、OllamaAI.summarize()
