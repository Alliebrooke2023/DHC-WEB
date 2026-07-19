"""Terminal REPL for the agent.

    python -m agent            # interactive session
    python -m agent -p "..."   # one-shot prompt, print reply, exit
    python -m agent --health   # check backend/model availability

Slash commands inside the REPL:
    /help /tools /skills /skill <name> [args] /tasks /memory
    /note <text> /journal <text> /brain /find <query>
    /model <name> /backend <name> /sessions /resume <file> /quit
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .core import Agent
from .llm import make_backend
from .tools import get_registry

BANNER = """\
agent v{version} — offline agent framework
backend: {backend} ({status})
tools: {ntools} | skills: {nskills} | plugins: {nplugins}
type a request, or /help for commands
"""


def _confirm(prompt: str) -> bool:
    try:
        ans = input(f"  allow {prompt}? [y/N] ").strip().lower()
    except EOFError:
        return False
    return ans in ("y", "yes")


def _print_event(kind: str, text: str) -> None:
    print(f"  · {text}")


def build_agent(workdir: Path | None = None, interactive: bool = True) -> Agent:
    config = load_config(workdir)
    confirm = _confirm if interactive else (lambda p: False)
    on_event = _print_event if interactive else None
    return Agent(config, confirm=confirm, on_event=on_event)


def handle_slash(agent: Agent, line: str) -> bool:
    """Handle a /command. Returns False if the REPL should exit."""
    parts = line[1:].split(" ", 2)
    cmd, rest = parts[0], parts[1:]

    if cmd in ("quit", "exit", "q"):
        return False
    elif cmd == "help":
        print(__doc__)
    elif cmd == "tools":
        for t in sorted(get_registry().values(), key=lambda t: t.name):
            flag = " (asks first)" if t.dangerous else ""
            print(f"  {t.name}{flag}: {t.description}")
    elif cmd == "skills":
        if not agent.skills:
            print("  (no skills found — add skills/<name>/SKILL.md)")
        for s in agent.skills.values():
            print(f"  {s.name}: {s.description}")
    elif cmd == "skill":
        if not rest:
            print("  usage: /skill <name> [args]")
        else:
            print(" ", agent.use_skill(rest[0], rest[1] if len(rest) > 1 else ""))
    elif cmd == "tasks":
        from .tools.tasks import _load, _render
        print(_render(_load(agent.ctx)))
    elif cmd == "memory":
        from .tools.memory import read_memory
        print(read_memory(agent.config) or "  (memory is empty)")
    elif cmd == "note":
        from .tools.brain import note_append
        if rest:
            text = " ".join(rest)
            print(" ", note_append(agent.ctx, title="inbox", content=text))
        else:
            print("  usage: /note <text>  (captures to the inbox note)")
    elif cmd == "journal":
        from .tools.brain import journal as _journal
        if rest:
            print(" ", _journal(agent.ctx, entry=" ".join(rest)))
        else:
            print("  usage: /journal <text>")
    elif cmd == "brain":
        from .tools.brain import brain_overview
        print(brain_overview(agent.ctx))
    elif cmd == "find":
        from .tools.brain import note_search
        if rest:
            print(note_search(agent.ctx, query=" ".join(rest)))
        else:
            print("  usage: /find <query>")
    elif cmd == "model":
        if rest:
            agent.config.model = rest[0]
            agent.backend = make_backend(agent.config)
        print(f"  model: {agent.config.model}")
    elif cmd == "backend":
        if rest:
            agent.config.backend = rest[0]
            try:
                agent.backend = make_backend(agent.config)
            except ValueError as e:
                print(f"  {e}")
        ok, status = agent.backend.health_check()
        print(f"  backend: {agent.config.backend} ({status})")
    elif cmd == "sessions":
        sdir = agent.config.state_dir / "sessions"
        for f in sorted(sdir.glob("*.json")) if sdir.is_dir() else []:
            print(f"  {f}")
    elif cmd == "resume":
        if rest:
            n = agent.resume(Path(rest[0]))
            print(f"  resumed {rest[0]} ({n} messages)")
        else:
            print("  usage: /resume <session-file>")
    else:
        print(f"  unknown command /{cmd} — try /help")
    return True


def repl(agent: Agent) -> None:
    ok, status = agent.backend.health_check()
    from . import __version__
    print(BANNER.format(version=__version__, backend=agent.config.backend,
                        status=status, ntools=len(get_registry()),
                        nskills=len(agent.skills), nplugins=len(agent.plugins)))
    if not ok:
        print(f"warning: backend not ready — {status}\n")

    while True:
        try:
            line = input("agent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.startswith("/"):
            if not handle_slash(agent, line):
                break
            continue
        try:
            reply = agent.run_turn(line)
        except KeyboardInterrupt:
            print("\n  (interrupted)")
            continue
        except Exception as e:
            print(f"  error: {e}")
            continue
        print(f"\n{reply}\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="agent", description="Offline agent framework")
    ap.add_argument("-p", "--prompt", help="one-shot prompt (non-interactive)")
    ap.add_argument("-C", "--workdir", type=Path, default=None, help="project directory")
    ap.add_argument("--backend", help="override backend: ollama | anthropic | echo")
    ap.add_argument("--model", help="override model name")
    ap.add_argument("--skill", help="load a skill before the prompt")
    ap.add_argument("--health", action="store_true", help="check backend health and exit")
    args = ap.parse_args(argv)

    agent = build_agent(args.workdir, interactive=args.prompt is None)
    if args.backend:
        agent.config.backend = args.backend
        agent.backend = make_backend(agent.config)
    if args.model:
        agent.config.model = args.model
        agent.backend = make_backend(agent.config)

    if args.health:
        ok, status = agent.backend.health_check()
        print(status)
        return 0 if ok else 1

    if args.skill:
        agent.use_skill(args.skill)

    if args.prompt is not None:
        print(agent.run_turn(args.prompt))
        return 0

    repl(agent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
