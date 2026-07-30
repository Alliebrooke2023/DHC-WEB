"""Example drop-in tool plugin.

Copy into .agent/tools/ in any project and the agent picks it up at startup.
"""

from agent.tools import tool


@tool()
def word_count(ctx, path: str) -> str:
    """Count lines, words, and characters in a text file."""
    text = (ctx.config.workdir / path).read_text(errors="replace")
    return f"{len(text.splitlines())} lines, {len(text.split())} words, {len(text)} chars"
