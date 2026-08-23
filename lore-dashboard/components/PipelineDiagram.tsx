const steps = ["GitLab MR", "Data Discovery", "Tokenize or Mask", "Model Boundary", "Protected Memory", "Safe Response"];

export function PipelineDiagram() {
  return <section className="border border-white/10 bg-[#0d0d0d] p-4"><p className="mb-3 text-xs font-medium text-zinc-500">Protection pipeline</p><div className="grid gap-px bg-white/10 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">{steps.map((step, index) => <div key={step} className="min-h-[86px] bg-[#0d0d0d] p-3"><div className="text-xs font-semibold text-emerald-400">0{index + 1}</div><div className="mt-3 text-xs font-medium text-zinc-100">{step}</div></div>)}</div></section>;
}
