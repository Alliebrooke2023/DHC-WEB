"""Task-list tools — lets the agent plan multi-step work and track progress,
persisted to .agent/tasks.json."""

from __future__ import annotations

import json

from . import tool

_STATES = ("pending", "in_progress", "completed")


def _load(ctx) -> list[dict]:
    p = ctx.config.state_dir / "tasks.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError:
            pass
    return []


def _save(ctx, items: list[dict]) -> None:
    (ctx.config.state_dir / "tasks.json").write_text(json.dumps(items, indent=2))


def _render(items: list[dict]) -> str:
    if not items:
        return "(no tasks)"
    marks = {"pending": " ", "in_progress": "~", "completed": "x"}
    return "\n".join(f"[{marks[t['state']]}] {i}. {t['title']}" for i, t in enumerate(items, 1))


@tool()
def task_add(ctx, title: str) -> str:
    """Add a task to the plan for the current piece of work."""
    items = _load(ctx)
    items.append({"title": title, "state": "pending"})
    _save(ctx, items)
    return _render(items)


@tool()
def task_update(ctx, number: int, state: str) -> str:
    """Set a task's state by its 1-based number: pending, in_progress, or completed."""
    if state not in _STATES:
        return f"ERROR: state must be one of {_STATES}"
    items = _load(ctx)
    if not 1 <= number <= len(items):
        return f"ERROR: no task #{number}; there are {len(items)} task(s)"
    items[number - 1]["state"] = state
    _save(ctx, items)
    return _render(items)


@tool()
def task_list(ctx) -> str:
    """Show the current task list and each task's state."""
    return _render(_load(ctx))


@tool()
def task_clear(ctx) -> str:
    """Remove all tasks (start a fresh plan)."""
    _save(ctx, [])
    return "(no tasks)"
