import Anthropic from "@anthropic-ai/sdk";
import { SYNTHESIZER_AGENT, WORKER_AGENTS, type AgentSpec } from "./agents";

const MODEL = process.env.HIVE_MIND_MODEL ?? "claude-sonnet-5";
const MAX_TOKENS = 1024;

export interface AgentContribution {
  role: string;
  label: string;
  content: string;
}

export interface HiveMindResult {
  task: string;
  contributions: AgentContribution[];
  synthesis: string;
}

function getClient(): Anthropic {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    throw new Error(
      "ANTHROPIC_API_KEY is not set. Add it to your environment to run the hive mind.",
    );
  }
  return new Anthropic({ apiKey });
}

async function runAgent(
  client: Anthropic,
  agent: AgentSpec,
  task: string,
  blackboard: AgentContribution[],
): Promise<string> {
  const blackboardText = blackboard
    .map((entry) => `### ${entry.label}\n${entry.content}`)
    .join("\n\n");

  const userMessage = blackboardText
    ? `Task:\n${task}\n\nShared blackboard so far:\n${blackboardText}`
    : `Task:\n${task}`;

  const response = await client.messages.create({
    model: MODEL,
    max_tokens: MAX_TOKENS,
    system: agent.systemPrompt,
    messages: [{ role: "user", content: userMessage }],
  });

  const textBlock = response.content.find((block) => block.type === "text");
  return textBlock && textBlock.type === "text" ? textBlock.text : "";
}

/**
 * Runs the worker agents sequentially (each one reads the prior agents'
 * output off the shared blackboard) and then a synthesizer that reconciles
 * everything into a single final answer.
 */
export async function runHiveMind(task: string): Promise<HiveMindResult> {
  const client = getClient();
  const blackboard: AgentContribution[] = [];

  for (const agent of WORKER_AGENTS) {
    const content = await runAgent(client, agent, task, blackboard);
    blackboard.push({ role: agent.role, label: agent.label, content });
  }

  const synthesis = await runAgent(client, SYNTHESIZER_AGENT, task, blackboard);

  return { task, contributions: blackboard, synthesis };
}
