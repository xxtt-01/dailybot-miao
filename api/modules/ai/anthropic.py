"""Anthropic Claude API 声明层"""
from api import apis

apis.declare("ai_anthropic", "messages", url="/v1/messages", method="POST")
