import {ArrowDownRight, ArrowUpRight} from "lucide-react";

type MetricCardProps = {label: string; value: string | number; hint?: string; trend?: string; negative?: boolean};

export function MetricCard({label, value, hint, trend = "Live", negative = false}: MetricCardProps) {
  return <div className="min-h-[164px] border border-white/10 bg-[#0d0d0d] p-4"><div className="text-sm font-medium text-zinc-100">{label}</div><div className="mt-7 text-3xl font-semibold tracking-tight text-white sm:text-4xl">{value}</div><div className={`mt-7 flex items-center gap-1 text-xs font-medium ${negative ? "text-rose-400" : "text-emerald-400"}`}>{negative ? <ArrowDownRight className="h-3.5 w-3.5" /> : <ArrowUpRight className="h-3.5 w-3.5" />}<span>{trend}</span>{hint ? <span className="font-normal text-zinc-500">{hint}</span> : null}</div></div>;
}
