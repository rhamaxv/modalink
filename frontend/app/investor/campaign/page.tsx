import type { Metadata } from "next";
import { CampaignList } from "@/components/CampaignList";

export const metadata: Metadata = {
  title: "Campaign saya - Modalink",
};

// Keputusan di layar ini: campaign mana yang perlu saya urus sekarang. Tidak
// ada sidebar, tidak ada kartu statistik: daftar itu sendiri sudah jawabannya.
// Tanpa "use client" di sini, hanya CampaignList yang menyimpan state fetch.
//
// Tombol "Buat campaign baru" sengaja TIDAK dirender di sini: ia dulu
// dirender dua kali (header di sini + aksi EmptyState di CampaignList) begitu
// daftar kosong, dua tombol aksen berlabel sama bersisian (laporan review).
// CampaignList sendiri yang memutuskan satu tempat tombol itu muncul, sesuai
// keadaan datanya.
export default function MyCampaignsPage() {
  return (
    <div className="mx-auto flex max-w-[72rem] flex-col gap-space-5 px-space-3 py-space-6">
      <div>
        <h1 className="font-display text-page text-ink">Campaign saya</h1>
        <p className="mt-space-3 max-w-measure text-body text-muted">
          Campaign dengan tenggat pengajuan paling dekat ditandai lebih menonjol.
        </p>
      </div>
      <CampaignList />
    </div>
  );
}
