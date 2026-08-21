export function RiskBadge({blocked, score}: {blocked?: boolean; score?: number}) {
  const label = blocked ? "Blocked" : score && score > 0.6 ? "Elevated" : "Allowed";
  const classes = blocked
    ? "border-rose/60 text-rose bg-rose/10"
    : score && score > 0.6
      ? "border-amber/60 text-amber bg-amber/10"
      : "border-teal/60 text-teal bg-teal/10";
  return <span className={`inline-flex items-center border px-2 py-1 text-xs font-semibold ${classes}`}>{label}</span>;
}
