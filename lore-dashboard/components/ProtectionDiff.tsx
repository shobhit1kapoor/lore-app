export function ProtectionDiff({input, output}: {input: string; output: string}) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="border border-line bg-[#111111] p-4">
        <div className="text-sm font-semibold text-zinc-300">Before</div>
        <pre className="mt-3 whitespace-pre-wrap text-sm leading-6 text-zinc-200">{input}</pre>
      </div>
      <div className="border border-line bg-[#111111] p-4">
        <div className="text-sm font-semibold text-zinc-300">After</div>
        <pre className="mt-3 whitespace-pre-wrap text-sm leading-6 text-teal">{output || "Run the demo to see protected text."}</pre>
      </div>
    </div>
  );
}
