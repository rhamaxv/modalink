import type { Metadata } from "next";
import { MilestoneApprovalFeed } from "@/components/MilestoneApprovalFeed";

export const metadata: Metadata = {
  title: "Milestone menunggu persetujuan - Modalink",
};

// Keputusan di layar ini: laporan ini cukup atau perlu direvisi. Tanpa
// "use client" di sini: hanya MilestoneApprovalFeed yang menyimpan state
// fetch, approve, dan reject.
export default function InvestorMilestonePage() {
  return (
    <div className="mx-auto flex max-w-[72rem] flex-col gap-space-5 px-space-3 py-space-6">
      <div>
        <h1 className="text-[clamp(2.5rem,5vw,4rem)] font-semibold leading-tight text-ink">
          Milestone menunggu persetujuan
        </h1>
        <p className="mt-space-2 max-w-measure text-base leading-[1.6] text-muted">
          Hanya proposal yang Anda danai sebagai lead investor dan sedang menunggu keputusan yang
          tampil di sini.
        </p>
      </div>
      <MilestoneApprovalFeed />
    </div>
  );
}
