import { NextRequest, NextResponse } from "next/server";
import { runHiveMind } from "@/lib/hivemind/orchestrator";

export async function POST(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const task = (body as { task?: unknown } | null)?.task;
  if (typeof task !== "string" || task.trim().length === 0) {
    return NextResponse.json(
      { error: "Request body must include a non-empty 'task' string" },
      { status: 400 },
    );
  }

  try {
    const result = await runHiveMind(task.trim());
    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    const status = message.includes("ANTHROPIC_API_KEY") ? 500 : 502;
    return NextResponse.json({ error: message }, { status });
  }
}
