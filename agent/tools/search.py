"""Content search tool (pure-python grep, so it works everywhere)."""

from __future__ import annotations

import re

from . import tool

_SKIP_DIRS = {".git", ".agent", "node_modules", "__pycache__", ".venv", "venv"}


@tool()
def grep(ctx, pattern: str, path: str = ".", glob: str = "*", max_results: int = 100) -> str:
    """Search file contents for a regex pattern; returns file:line:text matches."""
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return f"ERROR: invalid regex: {e}"

    root = (ctx.config.workdir / path).resolve()
    if not root.is_relative_to(ctx.config.workdir):
        return "ERROR: path escapes working directory"

    out = []
    for f in sorted(root.rglob(glob)):
        if not f.is_file() or any(part in _SKIP_DIRS for part in f.parts):
            continue
        try:
            text = f.read_text(errors="strict")
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable
        for i, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                out.append(f"{f.relative_to(ctx.config.workdir)}:{i}:{line.strip()[:200]}")
                if len(out) >= max_results:
                    return "\n".join(out) + "\n... (truncated)"
    return "\n".join(out) or "(no matches)"
