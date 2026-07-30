"""The agentic loop.

One turn: send conversation + tool schemas to the model; while it returns
tool calls, execute them and feed results back; stop when it replies with
plain text or the iteration cap is hit. Session transcripts persist to
.agent/sessions/ so a conversation can be resumed later.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .config import Config
from .llm import make_backend
from .skills import load_skills
from .tools import dispatch, get_registry, load_builtin_tools, load_plugins
from .tools.memory import read_memory

SYSTEM_PROMPT = """You are Agent, a capable offline coding and research assistant \
running in a terminal against the user's project directory.

Work agentically: when a request needs multiple steps, plan with the task \
tools, then execute step by step using your tools, checking results as you go. \
Prefer looking at real files over guessing. Use remember() for durable facts \
worth keeping across sessions. When you are done, reply with a concise summary \
of what you did — lead with the outcome.

Working directory: {workdir}
{memory_section}{skills_section}"""


@dataclass
class ToolEvent:
    name: str
    arguments: dict
    result: str


@dataclass
class AgentContext:
    """Handed to every tool as `ctx`."""
    config: Config
    confirm: Callable[[str], bool] = field(default=lambda prompt: True)


class Agent:
    def __init__(self, config: Config, confirm: Callable[[str], bool] | None = None,
                 on_event: Callable[[str, str], None] | None = None):
        self.config = config
        self.backend = make_backend(config)
        load_builtin_tools()
        self.plugins = load_plugins(config)
        self.skills = load_skills(config)
        self.ctx = AgentContext(config=config, confirm=confirm or (lambda p: True))
        self.on_event = on_event or (lambda kind, text: None)
        self.messages: list[dict] = [self._system_message()]
        self.session_file: Path | None = None

    # -- prompt assembly ---------------------------------------------------
    def _system_message(self) -> dict:
        memory = read_memory(self.config)
        memory_section = f"\nPersistent memory (facts from earlier sessions):\n{memory}\n" if memory.strip() else ""
        if self.skills:
            listing = "\n".join(f"- {s.name}: {s.description}" for s in self.skills.values())
            skills_section = ("\nAvailable skills (invoke by asking for them or via /skill):\n"
                              f"{listing}\n")
        else:
            skills_section = ""
        return {"role": "system", "content": SYSTEM_PROMPT.format(
            workdir=self.config.workdir, memory_section=memory_section,
            skills_section=skills_section)}

    def use_skill(self, name: str, args: str = "") -> str:
        skill = self.skills.get(name)
        if skill is None:
            return f"unknown skill {name!r}; available: {', '.join(sorted(self.skills))}"
        note = (f"[skill:{skill.name}] Follow these instructions for the next request.\n\n"
                f"{skill.instructions}")
        if args:
            note += f"\n\nArguments: {args}"
        self.messages.append({"role": "system", "content": note})
        return f"loaded skill {name}"

    # -- the loop ----------------------------------------------------------
    def run_turn(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})
        schemas = [t.to_openai() for t in get_registry().values()]
        registry = get_registry()

        for _ in range(self.config.max_iterations):
            resp = self.backend.chat(self.messages, tools=schemas)

            if not resp.wants_tools:
                self.messages.append({"role": "assistant", "content": resp.content})
                self._persist()
                return resp.content

            self.messages.append({
                "role": "assistant",
                "content": resp.content,
                "tool_calls": [tc.to_dict() for tc in resp.tool_calls],
            })
            for tc in resp.tool_calls:
                t = registry.get(tc.name)
                if t is not None and t.dangerous and self.config.confirm_shell:
                    desc = f"{tc.name}({json.dumps(tc.arguments)})"
                    if not self.ctx.confirm(desc):
                        result = "DENIED: the user declined this tool call."
                    else:
                        result = dispatch(self.ctx, tc.name, tc.arguments)
                else:
                    result = dispatch(self.ctx, tc.name, tc.arguments)
                self.on_event("tool", f"{tc.name}({json.dumps(tc.arguments)[:200]}) -> {result[:200]}")
                self.messages.append({"role": "tool", "tool_call_id": tc.id,
                                      "name": tc.name, "content": result})

        self._persist()
        return "(stopped: hit max_iterations tool-loop cap — raise it in config to continue)"

    # -- persistence -------------------------------------------------------
    def _persist(self) -> None:
        if self.session_file is None:
            sessions = self.config.state_dir / "sessions"
            sessions.mkdir(exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            self.session_file = sessions / f"{stamp}.json"
        self.session_file.write_text(json.dumps(self.messages, indent=2))

    def resume(self, session_path: Path) -> int:
        self.messages = json.loads(Path(session_path).read_text())
        self.session_file = Path(session_path)
        return len(self.messages)
