# DHC-WEB — Hive Mind

A multi-agent AI orchestration system: a task is dropped into a shared
"blackboard," a set of specialized Claude agents each contribute to it in
turn, and a final Synthesizer agent reconciles everything into one answer.

## Agents

| Agent | Role |
| --- | --- |
| Researcher | Surfaces relevant facts, background, and constraints |
| Analyst | Proposes concrete approaches or solutions |
| Critic | Finds flaws, risks, and edge cases in what's on the blackboard |
| Synthesizer | Produces the final answer from everything the others contributed |

Each agent (`src/lib/hivemind/agents.ts`) is just a system prompt and a
label. The orchestrator (`src/lib/hivemind/orchestrator.ts`) runs the
worker agents in sequence, appending each one's output to the blackboard
so later agents can build on earlier ones, then runs the Synthesizer over
the full blackboard.

## Running locally

```bash
npm install
cp .env.example .env.local   # add your ANTHROPIC_API_KEY
npm run dev
```

Open http://localhost:3000, describe a task, and submit it to see each
agent's contribution plus the synthesized final answer.

## API

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
