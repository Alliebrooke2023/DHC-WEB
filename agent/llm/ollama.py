"""Ollama backend — fully offline, talks to a local Ollama server.

Uses only the standard library (urllib), so the framework has zero
third-party dependencies and works air-gapped.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid

from .base import Backend, ChatResponse, ToolCall


class OllamaBackend(Backend):
    name = "ollama"

    def _post(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            self.config.ollama_url.rstrip("/") + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=600) as resp:
            return json.loads(resp.read().decode())

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> ChatResponse:
        # Ollama's /api/chat natively accepts OpenAI-style tool schemas and
        # the canonical message roles, with tool results as role "tool".
        payload = {
            "model": self.config.model,
            "messages": [self._to_ollama(m) for m in messages],
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_ctx": self.config.context_window,
            },
        }
        if tools:
            payload["tools"] = tools

        data = self._post("/api/chat", payload)
        msg = data.get("message", {})
        calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):  # some models return JSON strings
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"_raw": args}
            calls.append(ToolCall(id=tc.get("id") or uuid.uuid4().hex[:8],
                                  name=fn.get("name", ""), arguments=args))
        return ChatResponse(content=msg.get("content", "") or "", tool_calls=calls)

    @staticmethod
    def _to_ollama(m: dict) -> dict:
        if m["role"] == "assistant" and m.get("tool_calls"):
            return {
                "role": "assistant",
                "content": m.get("content", ""),
                "tool_calls": [
                    {"function": {"name": tc["name"], "arguments": tc["arguments"]}}
                    for tc in m["tool_calls"]
                ],
            }
        if m["role"] == "tool":
            return {"role": "tool", "content": m["content"]}
        return {"role": m["role"], "content": m["content"]}

    def health_check(self) -> tuple[bool, str]:
        try:
            req = urllib.request.Request(self.config.ollama_url.rstrip("/") + "/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                models = [m["name"] for m in json.loads(resp.read().decode()).get("models", [])]
            if self.config.model in models or any(m.startswith(self.config.model) for m in models):
                return True, f"ollama up, model {self.config.model} available"
            return False, (f"ollama up but model {self.config.model!r} not pulled. "
                           f"Run: ollama pull {self.config.model}")
        except (urllib.error.URLError, OSError) as e:
            return False, f"cannot reach ollama at {self.config.ollama_url}: {e}"
