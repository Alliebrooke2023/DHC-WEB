import Anthropic from "@anthropic-ai/sdk";
import {
  LEAD_AGENT,
  PARALLEL_AGENTS,
  SYNTHESIZER_AGENT,
  type AgentSpec,
} from "./agents";

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
 * Runs the Researcher first to seed the blackboard, then fans out to the
 * agents that only depend on those notes (Analyst, Critic) concurrently,
 * and finally runs the Synthesizer over the full blackboard. That is three
 * sequential round-trips instead of four, without any agent losing context
 * it actually reads.
 */
export async function runHiveMind(task: string): Promise<HiveMindResult> {
  const client = getClient();

  const research = await runAgent(client, LEAD_AGENT, task, []);
  const notes: AgentContribution[] = [
    { role: LEAD_AGENT.role, label: LEAD_AGENT.label, content: research },
  ];

  // Promise.all resolves in input order, so the blackboard stays in the
  // declared agent order regardless of which request finishes first.
  const parallel = await Promise.all(
    PARALLEL_AGENTS.map(async (agent) => ({
      role: agent.role,
      label: agent.label,
      content: await runAgent(client, agent, task, notes),
    })),
  );

  const blackboard = [...notes, ...parallel];
  const synthesis = await runAgent(client, SYNTHESIZER_AGENT, task, blackboard);

  return { task, contributions: blackboard, synthesis };
}
