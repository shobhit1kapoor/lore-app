export function RiskBadge({blocked, score}: {blocked?: boolean; score?: number}) {
  const label = blocked ? "Blocked" : score && score > 0.6 ? "Elevated" : "Allowed";
  const classes = blocked
    ? "border-rose text-rose bg-rose-50"
    : score && score > 0.6
      ? "border-amber text-amber bg-amber-50"
      : "border-teal text-teal bg-teal-50";
  return <span className={`inline-flex items-center border px-2 py-1 text-xs font-semibold ${classes}`}>{label}</span>;
}
