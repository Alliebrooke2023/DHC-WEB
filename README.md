# DHC-WEB

This repo holds two independent projects:

- [`src/`](#hive-mind-web-app) — **Hive Mind**, a Next.js multi-agent web app built on the Claude API.
- [`agent/`](#agent--an-offline-extensible-agent--second-brain) — **Agent**, an offline, extensible agent + second brain that runs against local models.

---

## Hive Mind (web app)

A multi-agent AI orchestration system: a task is dropped into a shared
"blackboard," a set of specialized Claude agents each contribute to it in
turn, and a final Synthesizer agent reconciles everything into one answer.

### Agents

| Agent | Role |
| --- | --- |
| Researcher | Surfaces relevant facts, background, and constraints |
| Analyst | Proposes concrete approaches or solutions |
| Critic | Finds flaws, risks, and edge cases the research implies |
| Synthesizer | Produces the final answer from everything the others contributed |

Each agent (`src/lib/hivemind/agents.ts`) is just a system prompt and a
label. The orchestrator (`src/lib/hivemind/orchestrator.ts`) runs the
Researcher first to seed the blackboard, then fans out to the Analyst and
the Critic **concurrently** — both read the research notes, neither reads
the other — and finally runs the Synthesizer over the full blackboard.
That is three sequential round-trips rather than four.

Adding a worker that only needs the research notes means appending it to
`PARALLEL_AGENTS`, and it joins the fan-out for free. A worker that has to
react to another worker's output does not fit this shape; fold that job
into the Synthesizer instead.

### Running locally

```bash
npm install
cp .env.example .env.local   # add your ANTHROPIC_API_KEY
npm run dev
```

Open http://localhost:3000, describe a task, and submit it to see each
agent's contribution plus the synthesized final answer.

### API

`POST /api/hive-mind` with `{ "task": "..." }` returns:

```json
{
  "task": "...",
  "contributions": [
    { "role": "researcher", "label": "Researcher", "content": "..." },
    { "role": "analyst", "label": "Analyst", "content": "..." },
    { "role": "critic", "label": "Critic", "content": "..." }
  ],
  "synthesis": "..."
}
```

---

## Agent — an offline, extensible agent + second brain

A Fable-5-style agent framework that runs **fully offline** against local
models (via [Ollama](https://ollama.com)), built in pure Python with **zero
third-party dependencies**. It pairs an agentic tool-calling loop with a
personal **second brain**: a markdown knowledge vault the agent captures to,
links, and retrieves from across sessions.

```
┌─────────────┐   messages + tool schemas   ┌──────────────────┐
│  REPL / CLI │ ──────────────────────────▶ │  Backend          │
│  (cli.py)   │                             │  ollama│anthropic │
└──────┬──────┘ ◀────────────────────────── │  │echo            │
       │            text or tool calls      └──────────────────┘
       ▼
┌─────────────┐    executes    ┌─────────────────────────────────┐
│ Agent loop  │ ─────────────▶ │ Tool registry                    │
│ (core.py)   │ ◀───────────── │ files·search·shell·memory·tasks  │
└─────────────┘    results     │ second-brain · your plugins      │
                               └─────────────────────────────────┘
```

### Quick start

```bash
# offline (default): needs Ollama + a tool-capable model
ollama pull qwen2.5:7b
python -m agent                 # interactive REPL
python -m agent -p "summarize this repo"   # one-shot
python -m agent --health        # is the backend ready?

# no model at all? exercise the loop with the test backend
python -m agent --backend echo -p 'hello'
```

Requires Python 3.10+. Nothing to `pip install`.

### The second brain

Notes are plain markdown in `brain/` — greppable, git-friendly, and
compatible with Obsidian-style `[[wiki links]]`. The agent uses it via
tools; you can also drive it directly from the REPL:

| Command | What it does |
|---|---|
| `/note <text>` | quick-capture to the inbox note |
| `/journal <text>` | timestamped entry in today's journal |
| `/find <query>` | full-text search across all notes |
| `/brain` | overview: counts, tags, recent + unlinked notes |

Model-facing tools: `note_create`, `note_append`, `note_read` (with
backlinks), `note_search`, `journal`, `brain_overview` — plus lightweight
fact memory (`remember`/`recall`/`forget`) that is injected into the system
prompt every session. Load the `second-brain` skill (`/skill second-brain`)
for a full capture→organize→connect→retrieve workflow.

### Adding a tool

Drop a typed, documented function in `.agent/tools/*.py` (auto-loaded) or in
`agent/tools/`:

```python
# .agent/tools/word_count.py
from agent.tools import tool

@tool()
def word_count(ctx, path: str) -> str:
    """Count the words in a text file."""
    text = (ctx.config.workdir / path).read_text()
    return f"{len(text.split())} words"
```

The JSON schema the model sees is derived from the signature and docstring.
Mark side-effecting tools `@tool(dangerous=True)` and the REPL will ask
before running them.

### Adding a skill

Skills are packaged instructions in markdown — new capabilities without code.
Create `skills/<name>/SKILL.md`:

```markdown
---
name: changelog
description: Draft a changelog entry from recent commits.
---
Run `git log --oneline -20`, group the commits by theme, and draft a
markdown changelog section.
```

Invoke with `/skill changelog` (or `--skill changelog` on the CLI). Bundled
skills: `second-brain`, `code-review`, `summarize`, `commit-message`.

### Built-in tools

| Area | Tools |
|---|---|
| Files | `read_file`, `write_file`, `edit_file`, `list_dir`, `glob_files` |
| Search | `grep` |
| Shell | `run_shell` *(asks first)* |
| Memory | `remember`, `recall`, `forget` |
| Planning | `task_add`, `task_update`, `task_list`, `task_clear` |
| Second brain | `note_create`, `note_append`, `note_read`, `note_search`, `journal`, `brain_overview` |

All file tools are sandboxed to the working directory; sessions persist to
`.agent/sessions/` and can be resumed with `/resume`.

### Configuration

`~/.agent/config.json` (user) or `.agent/config.json` (project), overridable
via `AGENT_*` env vars:

```json
{
  "backend": "ollama",
  "model": "qwen2.5:7b",
  "ollama_url": "http://localhost:11434",
  "max_iterations": 25,
  "confirm_shell": true,
  "brain_dir": "brain"
}
```

Set `"backend": "anthropic"` + `ANTHROPIC_API_KEY` to use the Claude API
when online — same tools, same skills, same brain.

### Tests

```bash
python -m unittest discover tests -v
```

The suite runs the full agent loop against the deterministic `echo` backend —
no model or network needed.
