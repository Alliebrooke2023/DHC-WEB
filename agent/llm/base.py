"""Backend-agnostic chat interface.

Every backend consumes a list of messages in a simple canonical form and
returns a ChatResponse. Canonical message shapes:

  {"role": "system"|"user"|"assistant", "content": str}
  {"role": "assistant", "content": str, "tool_calls": [ToolCall-dict, ...]}
  {"role": "tool", "tool_call_id": str, "name": str, "content": str}
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "arguments": self.arguments}


@dataclass
class ChatResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


class Backend:
    """Interface all model backends implement."""

    name = "base"

    def __init__(self, config):
        self.config = config

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> ChatResponse:
        """Send messages (+ optional tool schemas) and return the reply.

        `tools` uses OpenAI-style function schemas:
          {"type": "function", "function": {"name", "description", "parameters"}}
        Backends translate to their native format as needed.
        """
        raise NotImplementedError

    def health_check(self) -> tuple[bool, str]:
        """Return (ok, human-readable status)."""
        return True, "ok"
