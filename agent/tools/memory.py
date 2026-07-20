"""Persistent memory tools.

Facts are stored one-per-line in .agent/memory.md in the project, so
memory survives restarts, is human-editable, and diffs cleanly in git.
Current memory is also injected into the system prompt each session.
"""

from __future__ import annotations

from . import tool


def _memory_path(ctx):
    return ctx.config.state_dir / "memory.md"


def read_memory(config) -> str:
    p = config.state_dir / "memory.md"
    return p.read_text() if p.exists() else ""


@tool()
def remember(ctx, fact: str) -> str:
    """Save a fact to persistent memory so it is available in future sessions."""
    p = _memory_path(ctx)
    existing = p.read_text() if p.exists() else ""
    if fact.strip() in existing:
        return "already remembered"
    with p.open("a") as f:
        f.write(f"- {fact.strip()}\n")
    return f"remembered: {fact.strip()}"


@tool()
def recall(ctx, query: str = "") -> str:
    """Read persistent memory, optionally filtering lines by a substring."""
    text = read_memory(ctx.config)
    if not text:
        return "(memory is empty)"
    if query:
        hits = [ln for ln in text.splitlines() if query.lower() in ln.lower()]
        return "\n".join(hits) or f"(nothing in memory matching {query!r})"
    return text


@tool()
def forget(ctx, substring: str) -> str:
    """Delete memory lines containing the given substring."""
    p = _memory_path(ctx)
    if not p.exists():
        return "(memory is empty)"
    lines = p.read_text().splitlines()
    kept = [ln for ln in lines if substring.lower() not in ln.lower()]
    removed = len(lines) - len(kept)
    p.write_text("\n".join(kept) + ("\n" if kept else ""))
    return f"forgot {removed} item(s)"
