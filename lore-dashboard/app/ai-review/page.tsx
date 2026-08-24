import {AppShell} from "@/components/app-shell";
import {ProtectedAIReview} from "@/components/ProtectedAIReview";

export default function AIReviewPage() {
  return <AppShell><div className="space-y-6">
    <div><p className="text-xs font-medium uppercase tracking-[0.16em] text-emerald-400">Full working implementation</p><h1 className="mt-1 text-2xl font-semibold text-ink">Protected AI Review</h1><p className="mt-2 max-w-3xl text-sm text-zinc-400">A real end-to-end call: protect synthetic issue/MR context, run Protegrity input policy, send the minimum-necessary pseudonymized prompt to NVIDIA, scan the output, and write a hash-chained receipt.</p></div>
    <ProtectedAIReview />
  </div></AppShell>;
}
