"use client";

import {useState} from "react";
import Link from "next/link";
import {ShieldCheck} from "lucide-react";
import {postDemo} from "../lib/api";
import type {ProtectionResponse} from "../lib/types";
import {ProtectionDiff} from "./ProtectionDiff";

const sample = `Requester: Ada Lovelace
Email: ada@example.com
Account id: ACCT-778899
Debug token: debug_token sk-live-demo-secret

Please add this customer exception to the retry policy memory.`;

export function ProtectionDemo() {
  const [text, setText] = useState(sample);
  const [result, setResult] = useState<ProtectionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setLoading(true);
    setError("");
    try {
      setResult(await postDemo("/api/demo/protect", text));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Protection failed closed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <textarea className="min-h-48 w-full border border-line bg-[#111111] p-4 font-mono text-sm text-zinc-100 outline-none placeholder:text-zinc-600 focus:border-teal" value={text} onChange={(event) => setText(event.target.value)} />
      <button onClick={run} disabled={loading} className="inline-flex items-center gap-2 bg-teal px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">
        <ShieldCheck className="h-4 w-4" aria-hidden />
        {loading ? "Protecting" : "Run Protection"}
      </button>
      {error ? <div className="border border-rose/40 bg-rose/10 p-3 text-sm text-rose">{error}</div> : null}
      <ProtectionDiff input={text} output={result?.text || ""} />
      {result ? (
        <div className="border border-line bg-[#111111] p-4">
          <div className="text-sm font-semibold text-ink">Categories</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {result.categories.map((category) => <span key={category} className="bg-panel px-2 py-1 text-xs text-zinc-300">{category}</span>)}
          </div>
          <div className="mt-4 grid gap-3 border-t border-white/10 pt-4 sm:grid-cols-3">
            <div><div className="text-[10px] uppercase tracking-[0.12em] text-zinc-600">Provider</div><div className="mt-1 text-xs text-zinc-200">{result.provider || "Protegrity"}</div></div>
            <div><div className="text-[10px] uppercase tracking-[0.12em] text-zinc-600">Postcondition</div><div className="mt-1 text-xs text-emerald-400">Zero raw matches</div></div>
            <div><div className="text-[10px] uppercase tracking-[0.12em] text-zinc-600">Fingerprint</div><div className="mt-1 truncate font-mono text-[11px] text-zinc-400">{result.fingerprint || "generated in receipt"}</div></div>
          </div>
          <Link href={`/traces/${result.trace_id}`} className="mt-4 inline-flex text-xs font-semibold text-emerald-400 hover:text-emerald-300">Open protection receipt →</Link>
        </div>
      ) : null}
    </div>
  );
}
