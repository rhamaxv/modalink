"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CoverImage } from "@/components/ui/CoverImage";
import { ErrorState, LoadingState } from "@/components/ui";
import { SECTOR_ICON } from "@/components/CampaignBrowseCard";
import type { Proposal } from "@/components/ProposalCard";
import { ApiError, api } from "@/lib/api";
import { formatRupiah } from "@/lib/money";

const JUMLAH = 4;

type Keadaan =
  | { status: "loading" }
  | { status: "error"; pesan: string }
  | { status: "kosong" }
  | { status: "siap"; items: Proposal[] };

// Pengganti FeaturedProposalHighlight di hero halaman depan.
//
// Blok sebelumnya menampilkan SATU proposal sebagai sederet label bertumpuk
// ("Terbuka untuk pendanaan", nama usaha, "Dana diminta", nominal, "Baca
// proposal ini"), dan pemilik project meminta blok itu dihilangkan. Yang
// menggantikannya bukan hiasan: empat usaha nyata yang sedang mencari dana,
// dengan foto sampul yang mereka unggah sendiri.
//
// Empat, bukan satu: satu kotak di kolom kanan hero adalah kotak, sedangkan
// empat kotak membentuk bidang. Dan bukan delapan: hero tidak boleh menjadi
// daftar, daftarnya ada di /jelajah.
export function ProposalCoverWall() {
  const [keadaan, setKeadaan] = useState<Keadaan>({ status: "loading" });

  async function muat() {
    setKeadaan({ status: "loading" });
    try {
      const hasil = await api.get<{ items: Proposal[] }>(
        `/proposals?page_size=${JUMLAH}&sort=newest`,
      );
      const items = hasil.items ?? [];
      setKeadaan(items.length === 0 ? { status: "kosong" } : { status: "siap", items });
    } catch (error) {
      setKeadaan({
        status: "error",
        pesan:
          error instanceof ApiError
            ? error.message
            : "Terjadi kesalahan. Coba lagi sebentar lagi.",
      });
    }
  }

  useEffect(() => {
    muat();
  }, []);

  // Tinggi dipesan di semua keadaan supaya hero tidak melompat begitu
  // datanya datang.
  if (keadaan.status === "loading") {
    return <LoadingState label="Memuat usaha yang sedang mencari dana" minHeight={320} />;
  }
  if (keadaan.status === "error") {
    return <ErrorState message={keadaan.pesan} onRetry={muat} />;
  }
  if (keadaan.status === "kosong") {
    return (
      <div className="flex min-h-[320px] flex-col items-start justify-center gap-space-3 rounded-panel border border-line bg-panel px-space-5">
        <p className="max-w-measure text-body text-muted">
          Belum ada proposal yang terbuka untuk didanai saat ini.
        </p>
        <Link
          href="/daftar"
          className="inline-flex min-h-[44px] items-center text-body font-medium text-ink underline underline-offset-2"
        >
          Daftar sebagai UMKM
        </Link>
      </div>
    );
  }

  return (
    <ul className="grid grid-cols-2 gap-space-3">
      {keadaan.items.map((proposal) => (
        <li key={proposal.id}>
          <Link
            href={`/proposal/${proposal.id}`}
            className="group flex flex-col gap-space-2 rounded-card border border-line bg-panel p-space-2 transition-colors hover:border-line-strong hover:bg-panel-raised"
          >
            <CoverImage
              owner="proposals"
              id={proposal.id}
              coverUpdatedAt={proposal.cover_updated_at}
              nama={proposal.business_name}
              sectorIcon={proposal.sector ? SECTOR_ICON[proposal.sector] : undefined}
              ukuran="card"
            />
            <span className="truncate px-space-1 text-body font-semibold text-ink group-hover:underline">
              {proposal.business_name}
            </span>
            {/* Nominal tetap ada di tiap kotak: DESIGN.md menyebut nominal
                rupiah sebagai elemen grafis produk ini, dan foto sampul
                menambah bidangnya, bukan menggantikan angkanya. */}
            <span className="tabular px-space-1 pb-space-1 text-label text-muted">
              {formatRupiah(proposal.requested_amount)} dicari
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
