"""Tool registry.

Tools are plain functions registered with the @tool decorator. The JSON
schema for the model is derived from the function signature and docstring,
so adding a new tool is just writing a typed, documented function.

Drop-in plugins: any *.py file in a configured plugins dir (default
.agent/tools/) is loaded at startup; its @tool functions register
themselves automatically.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import sys
import traceback
from pathlib import Path
from typing import Callable

_REGISTRY: dict[str, "Tool"] = {}

_PY_TO_JSON = {str: "string", int: "integer", float: "number", bool: "boolean",
               list: "array", dict: "object"}


class Tool:
    def __init__(self, fn: Callable, name: str, description: str, dangerous: bool = False):
        self.fn = fn
        self.name = name
        self.description = description
        self.dangerous = dangerous
        self.schema = self._build_schema(fn)

    @staticmethod
    def _build_schema(fn: Callable) -> dict:
        sig = inspect.signature(fn)
        props, required = {}, []
        for pname, param in sig.parameters.items():
            if pname in ("ctx", "context"):  # injected, not model-visible
                continue
            ann = param.annotation if param.annotation is not inspect.Parameter.empty else str
            jtype = _PY_TO_JSON.get(ann, "string")
            props[pname] = {"type": jtype}
            if param.default is inspect.Parameter.empty:
                required.append(pname)
            else:
                props[pname]["description"] = f"optional, default: {param.default!r}"
        return {"type": "object", "properties": props, "required": required}

    def to_openai(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name, "description": self.description, "parameters": self.schema}}

    def __call__(self, ctx, **kwargs) -> str:
        params = inspect.signature(self.fn).parameters
        if "ctx" in params or "context" in params:
            key = "ctx" if "ctx" in params else "context"
            kwargs[key] = ctx
        result = self.fn(**kwargs)
        return result if isinstance(result, str) else json.dumps(result, indent=2, default=str)


def tool(name: str | None = None, dangerous: bool = False):
    """Register a function as an agent tool.

    The docstring's first paragraph becomes the tool description the model
    sees. Set dangerous=True for tools that mutate outside the sandbox
    (shell, deletes) so the REPL can require confirmation.
    """
    def wrap(fn: Callable) -> Callable:
        tname = name or fn.__name__
        desc = inspect.getdoc(fn) or tname
        desc = desc.split("\n\n")[0]
        _REGISTRY[tname] = Tool(fn, tname, desc, dangerous=dangerous)
        return fn
    return wrap


def get_registry() -> dict[str, Tool]:
    return dict(_REGISTRY)


def dispatch(ctx, name: str, arguments: dict) -> str:
    """Execute a registered tool; failures come back as error text, never raise."""
    t = _REGISTRY.get(name)
    if t is None:
        return f"ERROR: unknown tool {name!r}. Available: {', '.join(sorted(_REGISTRY))}"
    try:
        return t(ctx, **arguments)
    except TypeError as e:
        return f"ERROR: bad arguments for {name}: {e}. Schema: {json.dumps(t.schema)}"
    except Exception:
        return f"ERROR: tool {name} raised:\n{traceback.format_exc(limit=4)}"


def load_builtin_tools() -> None:
    from . import filesystem, search, shell, memory, tasks, brain  # noqa: F401


def load_plugins(config) -> list[str]:
    """Import every *.py in the configured plugin dirs; return loaded names."""
    loaded = []
    for rel in config.plugins_dirs:
        pdir = (config.workdir / rel).resolve()
        if not pdir.is_dir():
            continue
        for py in sorted(pdir.glob("*.py")):
            mod_name = f"agent_plugin_{py.stem}"
            try:
                spec = importlib.util.spec_from_file_location(mod_name, py)
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = mod
                spec.loader.exec_module(mod)
                loaded.append(py.name)
            except Exception as e:
                print(f"[plugins] failed to load {py}: {e}", file=sys.stderr)
    return loaded
