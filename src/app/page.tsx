"use client";

import { useState } from "react";
import type { AgentContribution, HiveMindResult } from "@/lib/hivemind/orchestrator";

type Status = "idle" | "loading" | "error";

export default function Home() {
  const [task, setTask] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<HiveMindResult | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!task.trim() || status === "loading") return;

    setStatus("loading");
    setError(null);
    setResult(null);

    try {
      const res = await fetch("/api/hive-mind", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error ?? "Request failed");
      }
      setResult(data as HiveMindResult);
      setStatus("idle");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setStatus("error");
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex w-full max-w-3xl flex-1 flex-col gap-8 px-6 py-16">
        <header className="flex flex-col gap-2">
          <h1 className="text-3xl font-semibold tracking-tight text-black dark:text-zinc-50">
            Hive Mind
          </h1>
          <p className="max-w-xl text-base leading-7 text-zinc-600 dark:text-zinc-400">
            Give the hive a task. A Researcher, an Analyst, and a Critic each
            contribute to a shared blackboard, then a Synthesizer folds their
            work into one final answer.
          </p>
        </header>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <textarea
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="Describe the task for the hive mind…"
            rows={4}
            className="w-full resize-none rounded-lg border border-black/10 bg-white p-4 text-base text-black outline-none focus:border-black/30 dark:border-white/15 dark:bg-zinc-900 dark:text-zinc-50 dark:focus:border-white/30"
          />
          <button
            type="submit"
            disabled={status === "loading" || !task.trim()}
            className="w-fit rounded-full bg-foreground px-6 py-3 text-sm font-medium text-background transition-colors hover:bg-[#383838] disabled:cursor-not-allowed disabled:opacity-50 dark:hover:bg-[#ccc]"
          >
            {status === "loading" ? "Running the hive…" : "Run hive mind"}
          </button>
        </form>

        {error && (
          <p className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            {error}
          </p>
        )}

        {result && (
          <div className="flex flex-col gap-6">
            <section className="flex flex-col gap-3">
              <h2 className="text-lg font-semibold text-black dark:text-zinc-50">
                Blackboard
              </h2>
              <div className="flex flex-col gap-3">
                {result.contributions.map((c: AgentContribution) => (
                  <article
                    key={c.role}
                    className="rounded-lg border border-black/10 bg-white p-4 dark:border-white/15 dark:bg-zinc-900"
                  >
                    <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                      {c.label}
                    </h3>
                    <p className="whitespace-pre-wrap text-sm leading-6 text-zinc-800 dark:text-zinc-200">
                      {c.content}
                    </p>
                  </article>
                ))}
              </div>
            </section>

            <section className="flex flex-col gap-3">
              <h2 className="text-lg font-semibold text-black dark:text-zinc-50">
                Final answer
              </h2>
              <article className="rounded-lg border border-black/20 bg-white p-4 dark:border-white/25 dark:bg-zinc-900">
                <p className="whitespace-pre-wrap text-sm leading-6 text-zinc-900 dark:text-zinc-100">
                  {result.synthesis}
                </p>
              </article>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
