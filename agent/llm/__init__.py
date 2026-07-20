from .base import Backend, ChatResponse, ToolCall
from .ollama import OllamaBackend
from .anthropic_api import AnthropicBackend
from .echo import EchoBackend


def make_backend(config) -> Backend:
    name = config.backend.lower()
    if name == "ollama":
        return OllamaBackend(config)
    if name == "anthropic":
        return AnthropicBackend(config)
    if name == "echo":
        return EchoBackend(config)
    raise ValueError(f"Unknown backend: {config.backend!r} (expected ollama, anthropic, or echo)")
