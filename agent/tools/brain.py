"""Second-brain tools: a personal knowledge vault the agent reads and writes.

Notes live as plain markdown in brain/ (configurable), one file per note,
with lightweight frontmatter (title, tags, created). Notes can reference
each other with [[wiki-links]]; backlinks are computed on demand. A daily
journal note (brain/journal/YYYY-MM-DD.md) collects quick captures.

Everything is plain text on disk: greppable, git-friendly, portable to
Obsidian or any other markdown vault.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from . import tool

_LINK_RX = re.compile(r"\[\[([^\]]+)\]\]")


def _vault(ctx) -> Path:
    v = ctx.config.workdir / getattr(ctx.config, "brain_dir", "brain")
    v.mkdir(parents=True, exist_ok=True)
    return v


def _slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s or "untitled"


def _note_path(ctx, title: str) -> Path:
    return _vault(ctx) / f"{_slug(title)}.md"


def _all_notes(ctx) -> list[Path]:
    return sorted(p for p in _vault(ctx).rglob("*.md") if p.is_file())


def _title_of(path: Path) -> str:
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("title:"):
            return line.split(":", 1)[1].strip()
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


@tool()
def note_create(ctx, title: str, content: str, tags: str = "") -> str:
    """Create a note in the second brain. Link related notes with [[Other Note]]. Tags are comma-separated."""
    p = _note_path(ctx, title)
    if p.exists():
        return f"ERROR: note already exists: {p.name} (use note_append or note_read)"
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    p.write_text(
        f"---\ntitle: {title}\ntags: {', '.join(tag_list)}\n"
        f"created: {time.strftime('%Y-%m-%d %H:%M')}\n---\n\n{content.strip()}\n"
    )
    return f"created note {p.name}"


@tool()
def note_append(ctx, title: str, content: str) -> str:
    """Append content to an existing note (creates it if missing)."""
    p = _note_path(ctx, title)
    if not p.exists():
        return note_create(ctx=ctx, title=title, content=content)
    with p.open("a") as f:
        f.write(f"\n{content.strip()}\n")
    return f"appended to {p.name}"


@tool()
def note_read(ctx, title: str) -> str:
    """Read a note by title, including its backlinks (notes that link to it)."""
    p = _note_path(ctx, title)
    if not p.exists():
        matches = [n for n in _all_notes(ctx) if _slug(title) in n.stem]
        if len(matches) == 1:
            p = matches[0]
        elif matches:
            return "multiple matches:\n" + "\n".join(n.stem for n in matches)
        else:
            return f"ERROR: no note titled {title!r}"
    body = p.read_text(errors="replace")
    backlinks = []
    for other in _all_notes(ctx):
        if other == p:
            continue
        links = {_slug(l) for l in _LINK_RX.findall(other.read_text(errors="replace"))}
        if p.stem in links:
            backlinks.append(other.stem)
    if backlinks:
        body += "\n\nBacklinks: " + ", ".join(backlinks)
    return body


@tool()
def note_search(ctx, query: str, tag: str = "") -> str:
    """Full-text search across all notes; optionally filter by tag. Returns note names with matching lines."""
    q = query.lower()
    out = []
    for p in _all_notes(ctx):
        text = p.read_text(errors="replace")
        if tag and not re.search(rf"tags:.*\b{re.escape(tag)}\b", text):
            continue
        hits = [ln.strip()[:150] for ln in text.splitlines() if q and q in ln.lower()]
        if hits or (tag and not q):
            out.append(f"{p.relative_to(_vault(ctx))}: " + (" | ".join(hits[:3]) if hits else "(tag match)"))
    return "\n".join(out[:50]) or "(no matching notes)"


@tool()
def journal(ctx, entry: str) -> str:
    """Add a timestamped entry to today's journal note in the second brain."""
    jdir = _vault(ctx) / "journal"
    jdir.mkdir(exist_ok=True)
    p = jdir / f"{time.strftime('%Y-%m-%d')}.md"
    if not p.exists():
        p.write_text(f"# Journal {time.strftime('%Y-%m-%d')}\n\n")
    with p.open("a") as f:
        f.write(f"- {time.strftime('%H:%M')} — {entry.strip()}\n")
    return f"journaled to {p.name}"


@tool()
def brain_overview(ctx) -> str:
    """Summarize the second brain: note count, tags in use, recent notes, orphan notes."""
    notes = _all_notes(ctx)
    if not notes:
        return "(second brain is empty — create the first note with note_create)"
    tags: dict[str, int] = {}
    linked: set[str] = set()
    for p in notes:
        text = p.read_text(errors="replace")
        m = re.search(r"tags:\s*(.+)", text)
        if m:
            for t in m.group(1).split(","):
                t = t.strip()
                if t:
                    tags[t] = tags.get(t, 0) + 1
        linked |= {_slug(l) for l in _LINK_RX.findall(text)}
    recent = sorted(notes, key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    orphans = [p.stem for p in notes if p.stem not in linked and "journal" not in p.parts][:10]
    lines = [f"{len(notes)} notes"]
    if tags:
        lines.append("tags: " + ", ".join(f"{t}({n})" for t, n in sorted(tags.items(), key=lambda kv: -kv[1])))
    lines.append("recent: " + ", ".join(p.stem for p in recent))
    if orphans:
        lines.append("unlinked notes: " + ", ".join(orphans))
    return "\n".join(lines)
