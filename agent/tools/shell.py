"""Shell execution tool — marked dangerous, so the REPL asks before running
unless confirm_shell is disabled in config."""

from __future__ import annotations

import subprocess

from . import tool


@tool(dangerous=True)
def run_shell(ctx, command: str, timeout: int = 120) -> str:
    """Run a shell command in the working directory and return stdout+stderr."""
    try:
        proc = subprocess.run(
            command, shell=True, cwd=ctx.config.workdir,
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"ERROR: command timed out after {timeout}s"
    out = (proc.stdout or "") + (proc.stderr or "")
    out = out[-20000:]  # keep transcripts bounded
    return f"exit code: {proc.returncode}\n{out or '(no output)'}"
