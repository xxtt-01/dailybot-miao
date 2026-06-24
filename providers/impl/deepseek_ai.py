"""DeepSeek AI 供应商（兼容 OpenAI API）"""
from .openai_ai import OpenAIAI


class DeepSeekAI(OpenAIAI):
    AI_PROVIDER_NAME = "deepseek"
