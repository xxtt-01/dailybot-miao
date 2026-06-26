"""Anthropic Claude AI 供应商"""
import httpx
from loguru import logger
from common.config import config
from ..modules.base_ai import BaseAIProvider


class AnthropicAI(BaseAIProvider):
    AI_PROVIDER_NAME = "anthropic"

    def __init__(self):
        super().__init__()

    def get_model_name(self):
        provider_cfg = config.get("models", {}).get("anthropic", {})
        models = provider_cfg.get("models", [])
        if models and isinstance(models, list):
            return models[0]
        return provider_cfg.get("model", "claude-sonnet-4-20250514")

    async def summarize(self, prompt, system_prompt=None, **kwargs):
        model = self.get_model_name()
        base_url = config.get("models.anthropic.base_url", "https://api.anthropic.com")
        api_key = config.get("models.anthropic.api_key", "")
        messages = [{"role": "user", "content": prompt}]
        payload = {"model": model, "messages": messages, "max_tokens": kwargs.get("max_tokens", 4096)}
        if system_prompt:
            payload["system"] = system_prompt
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
        custom_headers = config.get("models.anthropic.headers", {})
        if isinstance(custom_headers, dict):
            headers.update({k: str(v) for k, v in custom_headers.items()})
        if not api_key:
            logger.warning("⚠️ [Anthropic] API Key 未配置")
        try:
            logger.info(f"🤖 [Anthropic] 请求 {model}...")
            async with httpx.AsyncClient(verify=False) as client:
                resp = await client.post(
                    f"{base_url}/messages",
                    json=payload,
                    headers=headers,
                    timeout=kwargs.get("timeout", 120),
                )
                result = resp.json()
            if isinstance(result, dict):
                content = result.get("content", [])
                if content and isinstance(content, list):
                    return content[0].get("text", "")
            return str(result)
        except Exception as e:
            logger.error(f"❌ [Anthropic] 失败: {e}")
            raise
