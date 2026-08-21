import {AppShell} from "@/components/app-shell";
import {getMemories} from "@/lib/api";

export default async function MemoryPage() {
  const payload = await getMemories();
  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Protected Memory</h1>
          <p className="mt-1 text-sm text-slate-600">LORE wiki memories after the retrieval protection boundary.</p>
        </div>
        {payload.message ? <div className="border border-amber bg-amber-50 p-4 text-sm text-amber">{payload.message}</div> : null}
        <div className="grid gap-4">
          {payload.memories.length ? payload.memories.map((memory) => (
            <article key={memory.id} className="border border-line bg-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="font-semibold text-ink">#{memory.id} {memory.source_mr_title}</h2>
                <span className="border border-line px-2 py-1 text-xs text-slate-600">{memory.status}</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-700">{memory.decision}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {memory.governs_files.map((file) => <span key={file} className="bg-panel px-2 py-1 text-xs text-slate-700">{file}</span>)}
              </div>
            </article>
          )) : <div className="border border-dashed border-line bg-white p-6 text-sm text-slate-500">No protected memories available.</div>}
        </div>
      </div>
    </AppShell>
  );
}
