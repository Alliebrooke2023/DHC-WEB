export type AgentRole = "researcher" | "analyst" | "critic" | "synthesizer";

export interface AgentSpec {
  role: AgentRole;
  label: string;
  systemPrompt: string;
}

/**
 * Each agent gets the raw task plus the "blackboard" (the other agents'
 * findings so far) so the hive can build on shared context instead of
 * working in isolation.
 */
export const WORKER_AGENTS: AgentSpec[] = [
  {
    role: "researcher",
    label: "Researcher",
    systemPrompt:
      "You are the Researcher in a multi-agent hive mind. Given a task, " +
      "lay out the relevant facts, background, and constraints. Be concrete " +
      "and concise. Do not solve the task yourself, just surface what a " +
      "solver would need to know.",
  },
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
      "blackboard so far (research notes and proposed approaches), find " +
      "flaws, risks, and edge cases. Be direct and specific; do not " +
      "restate what's already correct.",
  },
];

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
