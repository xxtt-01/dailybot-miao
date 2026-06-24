"""Ollama API 声明层"""
from api import apis

apis.declare("ai_ollama", "chat", url="/v1/chat/completions", method="POST")
