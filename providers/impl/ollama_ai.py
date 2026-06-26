import httpx
from loguru import logger
from common.config import config
from ..modules.base_ai import BaseAIProvider


class OllamaAI(BaseAIProvider):
    AI_PROVIDER_NAME = "ollama"

    def __init__(self):
        super().__init__()

    def get_model_name(self):
        provider_cfg = config.get("models", {}).get("ollama", {})
        models = provider_cfg.get("models", [])
        if models and isinstance(models, list):
            return models[0]
        return provider_cfg.get("model", "qwen2.5:7b")

    async def summarize(self, prompt, system_prompt=None, **kwargs):
        model = self.get_model_name()
        base_url = config.get("models.ollama.base_url", "http://localhost:11434")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": model, "messages": messages, "temperature": kwargs.get("temperature", 0.7), "max_tokens": kwargs.get("max_tokens", 4096), "stream": False}
        try:
            logger.info(f"[Ollama] 请求 {model}...")
            async with httpx.AsyncClient(verify=False) as client:
                resp = await client.post(
                    f"{base_url}/v1/chat/completions",
                    json=payload,
                    timeout=kwargs.get("timeout", 120),
                )
                result = resp.json()
            if isinstance(result, dict):
                choices = result.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
            return str(result)
        except Exception as e:
            logger.error(f"[Ollama] 失败: {e}")
            raise
