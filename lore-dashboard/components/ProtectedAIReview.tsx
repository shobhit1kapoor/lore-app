"use client";

import Link from "next/link";
import {useState} from "react";
import {BrainCircuit, ShieldCheck} from "lucide-react";
import {runAIReview} from "../lib/api";
import type {AIReviewResponse} from "../lib/types";

const sample = `Synthetic merge request decision:
Requester: Ada Lovelace (ada@example.com)
Account: CUST-771900

Replace the shared Redis retry queue with an in-memory queue per API worker. Keep a 30-minute retry window and do not add cross-worker coordination.`;

export function ProtectedAIReview() {
  const [text, setText] = useState(sample);
  const [result, setResult] = useState<AIReviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(await runAIReview(text));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Protected AI review failed closed.");
    } finally {
      setLoading(false);
    }
  }

  return <div className="grid gap-5 xl:grid-cols-2">
    <section className="border border-white/10 bg-[#0d0d0d] p-5">
      <div className="flex items-center gap-2 text-sm font-semibold text-white"><BrainCircuit className="h-4 w-4 text-emerald-400" />Synthetic engineering context</div>
      <p className="mt-2 text-xs leading-5 text-zinc-500">Raw values remain inside the trusted input boundary. Protegrity protects the complete prompt before NVIDIA can be called.</p>
      <textarea aria-label="Synthetic engineering decision" className="mt-4 min-h-72 w-full border border-white/10 bg-[#111111] p-4 font-mono text-sm text-zinc-100 outline-none focus:border-emerald-400" value={text} onChange={(event) => setText(event.target.value)} />
      <button type="button" onClick={run} disabled={loading} className="mt-3 inline-flex items-center gap-2 bg-emerald-500 px-4 py-2 text-sm font-semibold text-black disabled:opacity-60"><ShieldCheck className="h-4 w-4" />{loading ? "Protecting and reviewing" : "Run protected AI review"}</button>
      {error ? <div className="mt-4 border border-rose/40 bg-rose/10 p-3 text-sm text-rose">{error}</div> : null}
    </section>

    <section className="border border-white/10 bg-[#0d0d0d] p-5">
      <div className="text-sm font-semibold text-white">Protected response</div>
      {!result ? <div className="mt-4 min-h-72 border border-dashed border-white/10 p-5 text-sm leading-6 text-zinc-600">Run the review to create a real Protegrity → NVIDIA → output-scan trace.</div> : <>
        <div className="mt-4 grid gap-px bg-white/10 sm:grid-cols-3">
          <div className="bg-[#111111] p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-zinc-600">Protection</div><div className="mt-1 text-xs text-emerald-400">{result.protection_provider}</div></div>
          <div className="bg-[#111111] p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-zinc-600">Model</div><div className="mt-1 text-xs text-zinc-200">{result.model_provider}</div></div>
          <div className="bg-[#111111] p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-zinc-600">Payload</div><div className="mt-1 text-xs text-emerald-400">{result.provider_payload_status}</div></div>
        </div>
        <div className="mt-4 min-h-56 whitespace-pre-wrap border border-white/10 bg-[#111111] p-4 text-sm leading-6 text-zinc-200">{result.response}</div>
        <Link href={`/traces/${result.trace_id}`} className="mt-4 inline-flex text-xs font-semibold text-emerald-400 hover:text-emerald-300">Open complete Protection Receipt →</Link>
      </>}
    </section>
  </div>;
}
