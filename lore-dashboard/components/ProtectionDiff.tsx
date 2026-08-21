export function ProtectionDiff({input, output}: {input: string; output: string}) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="border border-line bg-white p-4">
        <div className="text-sm font-semibold text-slate-700">Before</div>
        <pre className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-800">{input}</pre>
      </div>
      <div className="border border-line bg-white p-4">
        <div className="text-sm font-semibold text-slate-700">After</div>
        <pre className="mt-3 whitespace-pre-wrap text-sm leading-6 text-teal">{output || "Run the demo to see protected text."}</pre>
      </div>
    </div>
  );
}
