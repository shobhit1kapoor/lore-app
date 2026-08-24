const steps = [
  ["Authorize", "project + purpose"],
  ["Discover", "Protegrity entities"],
  ["Protect", "pseudonymize + envelope"],
  ["Guardrail", "input policy"],
  ["Retrieve", "scoped memory"],
  ["AI + tools", "minimum necessary"],
  ["Leak scan", "output + canaries"],
  ["Receipt", "hash-chained evidence"]
];

export function PipelineDiagram() {
  return <section className="border border-white/10 bg-[#0d0d0d] p-4"><div className="mb-4 flex flex-wrap items-end justify-between gap-2"><div><p className="text-xs font-medium uppercase tracking-[0.16em] text-emerald-400">Live protected path</p><h2 className="mt-1 text-base font-semibold text-white">Protegrity-centered AI pipeline</h2></div><p className="max-w-xl text-xs text-zinc-500">No persistence or model call is allowed before protection succeeds.</p></div><div className="grid gap-px bg-white/10 sm:grid-cols-2 lg:grid-cols-4">{steps.map(([step, detail], index) => <div key={step} className="min-h-[92px] bg-[#0d0d0d] p-3"><div className="flex items-center justify-between"><span className="text-xs font-semibold text-emerald-400">{String(index + 1).padStart(2, "0")}</span><span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_14px_rgba(52,211,153,.7)]" /></div><div className="mt-3 text-xs font-semibold text-zinc-100">{step}</div><div className="mt-1 text-[11px] text-zinc-500">{detail}</div></div>)}</div></section>;
}
