"""Optional Anthropic API backend (requires network + ANTHROPIC_API_KEY).

Kept dependency-free: calls the Messages API directly over urllib rather
than requiring the anthropic SDK.
"""

from __future__ import annotations

import json
import os
import urllib.request
import uuid

from .base import Backend, ChatResponse, ToolCall

API_URL = "https://api.anthropic.com/v1/messages"


class AnthropicBackend(Backend):
    name = "anthropic"

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> ChatResponse:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set (or use the ollama backend for offline)")

        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        payload = {
            "model": self.config.anthropic_model,
            "max_tokens": 4096,
            "messages": self._convert_messages(messages),
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [
                {
                    "name": t["function"]["name"],
                    "description": t["function"].get("description", ""),
                    "input_schema": t["function"].get("parameters", {"type": "object"}),
                }
                for t in tools
            ]

        req = urllib.request.Request(
            API_URL,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode())

        text, calls = "", []
        for block in data.get("content", []):
            if block["type"] == "text":
                text += block["text"]
            elif block["type"] == "tool_use":
                calls.append(ToolCall(id=block.get("id", uuid.uuid4().hex[:8]),
                                      name=block["name"], arguments=block.get("input", {})))
        return ChatResponse(content=text, tool_calls=calls)

    @staticmethod
    def _convert_messages(messages: list[dict]) -> list[dict]:
        out = []
        for m in messages:
            if m["role"] == "system":
                continue
            if m["role"] == "assistant" and m.get("tool_calls"):
                content = []
                if m.get("content"):
                    content.append({"type": "text", "text": m["content"]})
                for tc in m["tool_calls"]:
                    content.append({"type": "tool_use", "id": tc["id"],
                                    "name": tc["name"], "input": tc["arguments"]})
                out.append({"role": "assistant", "content": content})
            elif m["role"] == "tool":
                out.append({"role": "user", "content": [{
                    "type": "tool_result", "tool_use_id": m["tool_call_id"],
                    "content": m["content"],
                }]})
            else:
                out.append({"role": m["role"], "content": m["content"]})
        return out

    def health_check(self) -> tuple[bool, str]:
        if os.environ.get("ANTHROPIC_API_KEY"):
            return True, f"anthropic backend, model {self.config.anthropic_model}"
        return False, "ANTHROPIC_API_KEY not set"
