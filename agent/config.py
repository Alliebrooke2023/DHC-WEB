"""Configuration for Agent.

Resolution order (highest wins):
  1. Environment variables (AGENT_*)
  2. Project config: ./.agent/config.json
  3. User config:    ~/.agent/config.json
  4. Built-in defaults
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


DEFAULTS = {
    "backend": "ollama",            # ollama | anthropic | echo
    "model": "qwen2.5:7b",          # any tool-capable local model
    "ollama_url": "http://localhost:11434",
    "anthropic_model": "claude-sonnet-5",
    "max_iterations": 25,           # tool-loop safety cap
    "temperature": 0.4,
    "context_window": 32768,
    "confirm_shell": True,          # ask before running shell commands
    "skills_dirs": ["skills"],      # relative to project root, plus ~/.agent/skills
    "plugins_dirs": [".agent/tools"],
    "brain_dir": "brain",           # second-brain markdown vault
}


@dataclass
class Config:
    backend: str = DEFAULTS["backend"]
    model: str = DEFAULTS["model"]
    ollama_url: str = DEFAULTS["ollama_url"]
    anthropic_model: str = DEFAULTS["anthropic_model"]
    max_iterations: int = DEFAULTS["max_iterations"]
    temperature: float = DEFAULTS["temperature"]
    context_window: int = DEFAULTS["context_window"]
    confirm_shell: bool = DEFAULTS["confirm_shell"]
    skills_dirs: list = field(default_factory=lambda: list(DEFAULTS["skills_dirs"]))
    plugins_dirs: list = field(default_factory=lambda: list(DEFAULTS["plugins_dirs"]))
    brain_dir: str = DEFAULTS["brain_dir"]
    workdir: Path = field(default_factory=Path.cwd)

    @property
    def state_dir(self) -> Path:
        d = self.workdir / ".agent"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def user_dir(self) -> Path:
        d = Path.home() / ".agent"
        d.mkdir(parents=True, exist_ok=True)
        return d


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def load_config(workdir: Path | None = None) -> Config:
    workdir = (workdir or Path.cwd()).resolve()
    merged = dict(DEFAULTS)
    merged.update(_read_json(Path.home() / ".agent" / "config.json"))
    merged.update(_read_json(workdir / ".agent" / "config.json"))

    env_map = {
        "AGENT_BACKEND": "backend",
        "AGENT_MODEL": "model",
        "AGENT_OLLAMA_URL": "ollama_url",
        "AGENT_ANTHROPIC_MODEL": "anthropic_model",
        "AGENT_MAX_ITERATIONS": "max_iterations",
        "AGENT_TEMPERATURE": "temperature",
    }
    for env, key in env_map.items():
        if env in os.environ:
            raw = os.environ[env]
            if key in ("max_iterations",):
                merged[key] = int(raw)
            elif key in ("temperature",):
                merged[key] = float(raw)
            else:
                merged[key] = raw

    known = {f for f in Config.__dataclass_fields__ if f != "workdir"}
    return Config(workdir=workdir, **{k: v for k, v in merged.items() if k in known})
