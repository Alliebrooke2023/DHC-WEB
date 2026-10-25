"""Path containment helpers shared by the file-touching tools.

Every tool that turns model-supplied input into a filesystem path goes
through here. Keeping it in one place is deliberate: the sandbox hole this
module was written to close existed because `grep` and `glob_files` each
grew their own partial version of the check, and both missed that a glob
pattern is exactly as attacker-controlled as a path is.
"""

from __future__ import annotations

from pathlib import Path


def resolve_in_workdir(ctx, path: str) -> Path:
    """Resolve path against the workdir, rejecting anything that escapes it."""
    p = (ctx.config.workdir / path).resolve()
    if not p.is_relative_to(ctx.config.workdir):
        raise ValueError(f"path escapes working directory: {path}")
    return p


def contains(ctx, p: Path) -> bool:
    """True if p really lives inside the workdir, after following symlinks."""
    try:
        return p.resolve().is_relative_to(ctx.config.workdir)
    except OSError:
        return False


def glob_in(ctx, root: Path, pattern: str, recursive: bool = False) -> list[Path]:
    """Glob under root, returning only files that stay inside the workdir.

    A pattern traverses as freely as a path does — '../../*' walks out of
    the sandbox, and on newer Pythons an absolute pattern ignores root
    entirely — and a matched symlink can point anywhere. So matches are
    filtered by where they actually resolve to rather than trusted, and
    anything outside is dropped silently instead of being reported back.
    """
    if Path(pattern).is_absolute():
        raise ValueError(f"glob pattern must be relative to the workdir: {pattern}")
    try:
        matches = root.rglob(pattern) if recursive else root.glob(pattern)
        return sorted(p for p in matches if p.is_file() and contains(ctx, p))
    except (NotImplementedError, ValueError) as e:
        raise ValueError(f"invalid glob pattern {pattern!r}: {e}") from None
