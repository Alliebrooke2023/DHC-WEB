"""Echo backend — deterministic stub for tests and offline dry-runs.

Understands a tiny scripting convention: a user message of the form
  !tool <name> <json-args>
produces a tool call; anything else is echoed back. This lets the whole
agent loop (registry, execution, transcripts) be exercised with no model.
"""

from __future__ import annotations

import json
import uuid

from .base import Backend, ChatResponse, ToolCall


class EchoBackend(Backend):
    name = "echo"

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> ChatResponse:
        last = messages[-1]
        if last["role"] == "tool":
            return ChatResponse(content=f"[echo] tool result: {last['content'][:2000]}")

        text = last.get("content", "")
        if text.startswith("!tool "):
            try:
                _, name, *rest = text.split(" ", 2)
                args = json.loads(rest[0]) if rest else {}
            except (ValueError, json.JSONDecodeError):
                return ChatResponse(content="[echo] bad !tool syntax, expected: !tool name {json}")
            return ChatResponse(tool_calls=[ToolCall(id=uuid.uuid4().hex[:8], name=name, arguments=args)])
        return ChatResponse(content=f"[echo] {text}")

    def health_check(self) -> tuple[bool, str]:
        return True, "echo backend (no model)"
