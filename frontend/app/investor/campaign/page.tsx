import type { Metadata } from "next";
import Link from "next/link";
import { CampaignList } from "@/components/CampaignList";

export const metadata: Metadata = {
  title: "Campaign saya - Modalink",
};

// Keputusan di layar ini: campaign mana yang perlu saya urus sekarang. Tidak
// ada sidebar, tidak ada kartu statistik: daftar itu sendiri sudah jawabannya.
// Tanpa "use client" di sini, hanya CampaignList yang menyimpan state fetch.
export default function MyCampaignsPage() {
  return (
    <div className="mx-auto flex max-w-[72rem] flex-col gap-space-5 px-space-3 py-space-6">
      <div className="flex flex-wrap items-start justify-between gap-space-3">
        <div>
          <h1 className="text-[clamp(2.5rem,5vw,4rem)] font-semibold leading-tight text-ink">
            Campaign saya
          </h1>
          <p className="mt-space-2 max-w-measure text-base leading-[1.6] text-muted">
            Campaign dengan tenggat pengajuan paling dekat ditandai lebih menonjol.
          </p>
        </div>
        <Link
          href="/investor/campaign/baru"
          className="inline-flex min-h-[44px] items-center rounded-sm bg-accent px-space-4 py-space-2 text-base font-semibold text-on-accent"
        >
          Buat campaign baru
        </Link>
      </div>
      <CampaignList />
    </div>
  );
}
