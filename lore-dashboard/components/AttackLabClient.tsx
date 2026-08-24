"use client";

import Link from "next/link";
import {useEffect, useState} from "react";
import {FlaskConical, ShieldCheck} from "lucide-react";
import {getAttacks, runAttack} from "../lib/api";
import type {AttackScenario, ProtectionResponse} from "../lib/types";
import {RiskBadge} from "./RiskBadge";

export function AttackLabClient() {
  const [scenarios, setScenarios] = useState<AttackScenario[]>([]);
  const [selected, setSelected] = useState<AttackScenario | null>(null);
  const [text, setText] = useState("");
  const [result, setResult] = useState<ProtectionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getAttacks().then((items) => {
      setScenarios(items);
      if (items[0]) {
        setSelected(items[0]);
        setText(items[0].prompt);
      }
    });
  }, []);

  function choose(scenario: AttackScenario) {
    setSelected(scenario);
    setText(scenario.prompt);
    setResult(null);
    setError("");
  }

  async function run() {
    if (!selected) return;
    setLoading(true);
    setError("");
    try {
      setResult(await runAttack(selected.id, text));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Attack probe failed closed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(360px,.9fr)]">
      <section className="border border-white/10 bg-[#0d0d0d]">
        <div className="border-b border-white/10 p-4">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">Synthetic adversarial catalog</p>
          <h2 className="mt-1 text-lg font-semibold text-white">Eight protected boundaries</h2>
        </div>
        <div className="grid gap-px bg-white/10 sm:grid-cols-2">
          {scenarios.map((scenario) => (
            <button key={scenario.id} type="button" onClick={() => choose(scenario)} className={`min-h-32 bg-[#0d0d0d] p-4 text-left transition hover:bg-white/[0.03] ${selected?.id === scenario.id ? "ring-1 ring-inset ring-emerald-400" : ""}`}>
              <div className="flex items-center justify-between gap-3"><span className="font-mono text-xs text-emerald-400">{scenario.id}</span><span className="text-[10px] uppercase tracking-[0.12em] text-zinc-600">{scenario.category.replaceAll("_", " ")}</span></div>
              <div className="mt-5 text-sm font-semibold text-zinc-100">{scenario.title}</div>
              <div className="mt-2 text-xs text-zinc-500">Expected boundary: {scenario.boundary.replaceAll("_", " ")}</div>
            </button>
          ))}
        </div>
      </section>

      <section className="border border-white/10 bg-[#0d0d0d] p-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-white"><FlaskConical className="h-4 w-4 text-rose" />Run selected probe</div>
        <textarea aria-label="Attack prompt" className="mt-4 min-h-48 w-full border border-line bg-[#111111] p-4 font-mono text-sm text-zinc-100 outline-none placeholder:text-zinc-600 focus:border-rose" value={text} onChange={(event) => setText(event.target.value)} />
        <button onClick={run} disabled={loading || !selected} className="mt-3 inline-flex items-center gap-2 bg-rose px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">
          <FlaskConical className="h-4 w-4" aria-hidden />
          {loading ? "Testing boundary" : "Run attack probe"}
        </button>
        {error ? <div className="mt-4 border border-rose/40 bg-rose/10 p-3 text-sm text-rose">{error}</div> : null}
        {result ? (
          <div className="mt-5 border border-line bg-[#111111] p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 font-semibold text-ink"><ShieldCheck className="h-4 w-4 text-emerald-400" />Boundary decision</div>
                <div className="mt-2 text-sm text-zinc-400">{result.reason || "Assessed by Protegrity Semantic Guardrails."}</div>
              </div>
              <RiskBadge blocked={result.blocked} score={result.risk_score} />
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="border border-white/10 p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-zinc-600">Blocked at</div><div className="mt-1 text-xs text-zinc-200">{result.blocked_boundary?.replaceAll("_", " ") || selected?.boundary.replaceAll("_", " ")}</div></div>
              <div className="border border-white/10 p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-zinc-600">Provider</div><div className="mt-1 text-xs text-zinc-200">{result.provider || "Protegrity"}</div></div>
            </div>
            <pre className="mt-4 whitespace-pre-wrap bg-panel p-4 text-sm text-zinc-200">{result.text}</pre>
            <Link href={`/traces/${result.trace_id}`} className="mt-4 inline-flex text-xs font-semibold text-emerald-400 hover:text-emerald-300">Open protection receipt →</Link>
          </div>
        ) : null}
      </section>
    </div>
  );
}
