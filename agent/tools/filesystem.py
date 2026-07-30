"""Filesystem tools: read, write, edit, list, glob.

All paths resolve inside the agent's working directory; escapes are
rejected so the model can't wander the host filesystem.
"""

from __future__ import annotations

from pathlib import Path

from . import tool


def _resolve(ctx, path: str) -> Path:
    p = (ctx.config.workdir / path).resolve()
    if not p.is_relative_to(ctx.config.workdir):
        raise ValueError(f"path escapes working directory: {path}")
    return p


@tool()
def read_file(ctx, path: str, offset: int = 0, limit: int = 500) -> str:
    """Read a text file, returning numbered lines. Use offset/limit for large files."""
    p = _resolve(ctx, path)
    lines = p.read_text(errors="replace").splitlines()
    window = lines[offset:offset + limit]
    body = "\n".join(f"{i + offset + 1:>5}\t{ln}" for i, ln in enumerate(window))
    suffix = f"\n... ({len(lines) - offset - limit} more lines)" if len(lines) > offset + limit else ""
    return body + suffix if body else "(empty file)"


@tool()
def write_file(ctx, path: str, content: str) -> str:
    """Create or overwrite a text file with the given content."""
    p = _resolve(ctx, path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"wrote {len(content)} chars to {path}"


@tool()
def edit_file(ctx, path: str, old_string: str, new_string: str) -> str:
    """Replace an exact string in a file. old_string must occur exactly once."""
    p = _resolve(ctx, path)
    text = p.read_text()
    n = text.count(old_string)
    if n == 0:
        return "ERROR: old_string not found in file"
    if n > 1:
        return f"ERROR: old_string occurs {n} times; provide more surrounding context to make it unique"
    p.write_text(text.replace(old_string, new_string, 1))
    return f"edited {path}"


@tool()
def list_dir(ctx, path: str = ".") -> str:
    """List files and directories at a path (directories get a trailing /)."""
    p = _resolve(ctx, path)
    entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name))
    return "\n".join(e.name + ("/" if e.is_dir() else "") for e in entries) or "(empty)"


@tool()
def glob_files(ctx, pattern: str) -> str:
    """Find files matching a glob pattern like '**/*.py', relative to the workdir."""
    root = ctx.config.workdir
    hits = [str(p.relative_to(root)) for p in sorted(root.glob(pattern)) if p.is_file()]
    hits = [h for h in hits if not h.startswith((".git/", ".agent/"))]
    return "\n".join(hits[:500]) or "(no matches)"
