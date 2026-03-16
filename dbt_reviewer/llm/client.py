import anthropic
from typing import Optional


class AnthropicClient:
    def __init__(self, model: str = "claude-sonnet-4-6"):
        self._client = anthropic.Anthropic()
        self.model = model

    def create_message(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> anthropic.types.Message:
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools
        return self._client.messages.create(**kwargs)
