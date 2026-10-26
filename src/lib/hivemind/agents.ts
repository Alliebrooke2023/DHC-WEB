export type AgentRole = "researcher" | "analyst" | "critic" | "synthesizer";

export interface AgentSpec {
  role: AgentRole;
  label: string;
  systemPrompt: string;
}

/**
 * The Researcher opens the blackboard: it runs first, on the raw task, and
 * its notes become the shared context every later agent reads.
 */
export const LEAD_AGENT: AgentSpec = {
  role: "researcher",
  label: "Researcher",
  systemPrompt:
    "You are the Researcher in a multi-agent hive mind. Given a task, " +
    "lay out the relevant facts, background, and constraints. Be concrete " +
    "and concise. Do not solve the task yourself, just surface what a " +
    "solver would need to know.",
};

/**
 * These agents each read the task plus the Researcher's notes, but not each
 * other's output, so the orchestrator runs them concurrently. Keep them
 * mutually independent — anything that needs to react to another worker's
 * contribution belongs in the Synthesizer instead.
 */
export const PARALLEL_AGENTS: AgentSpec[] = [
  {
    role: "analyst",
    label: "Analyst",
    systemPrompt:
      "You are the Analyst in a multi-agent hive mind. Given a task and the " +
      "Researcher's notes on the shared blackboard, propose one or more " +
      "concrete approaches or solutions. Be specific and structured.",
  },
  {
    role: "critic",
    label: "Critic",
    systemPrompt:
      "You are the Critic in a multi-agent hive mind. Given a task and the " +
      "Researcher's notes on the shared blackboard, find the flaws, risks, " +
      "and edge cases that any proposed solution will have to survive. You " +
      "are working in parallel with the Analyst, so you will not see their " +
      "proposal — critique the task and the research itself rather than " +
      "reviewing a specific approach. Be direct and specific.",
  },
];

/** Display order for the blackboard: the lead agent, then the parallel pair. */
export const WORKER_AGENTS: AgentSpec[] = [LEAD_AGENT, ...PARALLEL_AGENTS];

export const SYNTHESIZER_AGENT: AgentSpec = {
  role: "synthesizer",
  label: "Synthesizer",
  systemPrompt:
    "You are the Synthesizer in a multi-agent hive mind. You receive the " +
    "original task plus the full blackboard contributed by the Researcher, " +
    "Analyst, and Critic. Produce one clear, final answer that resolves " +
    "the task, incorporating the strongest points and addressing the " +
    "critic's concerns. Do not mention the other agents by name in the " +
    "final answer.",
};
