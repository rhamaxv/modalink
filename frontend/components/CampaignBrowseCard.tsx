"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Amount, EmptyState, ErrorState, LoadingState } from "@/components/ui";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ApiError, api } from "@/lib/api";

// Bentuk ini mengikuti CampaignOut persis (backend/app/schemas/campaign.py):
// dua deadline terpisah (BR-64/D-16), bukan satu, dan tidak ada field
// "collected_amount" atau progres funding karena campaign itu sendiri tidak
// menyimpan dana, proposal di dalamnya yang menyimpannya. Menampilkan bilah
// progres di sini berarti mengarang angka (R-17).
export type PublicCampaign = {
  id: string;
  investor_id: string;
  title: string;
  description: string;
  sector: string;
  target_amount: number;
  apply_deadline: string;
  funding_deadline: string;
  score_threshold: number;
  status: string;
  created_at: string;
};

// Enam sektor tetap dari backend/app/models/campaign.py (Sector StrEnum).
// Diekspor supaya CampaignDetailPanel memakai pemetaan yang sama, bukan
// menyalin ulang enum ini di dua tempat yang bisa diam-diam menyimpang.
export const SECTOR_LABEL: Record<string, string> = {
  kuliner: "Kuliner",
  kerajinan: "Kerajinan",
  pertanian: "Pertanian",
  jasa: "Jasa",
  ritel: "Ritel",
  teknologi: "Teknologi",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" });
}

type CampaignBrowseCardProps = {
  campaign: PublicCampaign;
  /** Campaign dengan tenggat pengajuan paling dekat mendapat nominal lebih besar. */
  featured?: boolean;
  /** Urutan tampil, dipakai untuk penanda angka pada daftar bernomor. */
  index?: number;
};

export function CampaignBrowseCard({ campaign, featured = false, index }: CampaignBrowseCardProps) {
  return (
    // Satu set kelas untuk kartu biasa maupun unggulan, sama seperti
    // ProposalCard: hierarkinya datang dari ukuran nominal, bukan dari
    // border atau latar yang berbeda.
    <article className="flex flex-col gap-space-3 rounded-card border border-line bg-panel-raised px-space-4 py-space-4">
      <div className="flex flex-wrap items-start justify-between gap-space-2">
        <div className="flex items-baseline gap-space-2">
          {index !== undefined && (
            <span aria-hidden="true" className="tabular text-label font-medium text-muted">
              {String(index + 1).padStart(2, "0")}
            </span>
          )}
          <h3 className="text-card-title font-semibold text-ink">{campaign.title}</h3>
        </div>
        <StatusBadge status={campaign.status} />
      </div>
      <div className="flex flex-wrap items-center gap-space-2">
        {/* Chip accent-2 sebagai LATAR berpasangan dengan on-accent: kombinasi
            ini terukur aman di kedua tema (DESIGN.md). accent-2 sebagai warna
            TEKS polos gagal kontras di tema terang (lihat
            tests/accent-contrast.test.ts), jadi label kategori tidak pernah
            ditulis sebagai teks berwarna lepas. */}
        <span className="inline-flex w-fit items-center rounded-pill bg-accent-2 px-space-3 py-space-1 text-label font-medium text-on-accent">
          {SECTOR_LABEL[campaign.sector] ?? campaign.sector}
        </span>
        {featured && (
          // Penanda kedua, bukan dekorasi acak: campaign ini sungguh punya
          // tenggat pengajuan paling dekat di antara yang terbuka (dihitung
          // di CampaignBrowseList), bukan kartu pertama yang dipilih sembarang.
          <span className="inline-flex w-fit items-center rounded-pill bg-accent-2 px-space-3 py-space-1 text-label font-medium text-on-accent">
            Tenggat pengajuan paling dekat
          </span>
        )}
      </div>
      <Amount label="Dana target" amount={campaign.target_amount} size={featured ? "large" : "medium"} />
      {/* D-16: dua tenggat, label berbeda, tidak pernah hanya satu. Satu
          mengikat pengajuan proposal, satu mengikat pendanaannya. Tenggat
          pengajuan kartu unggulan ditulis dengan accent-text: --accent
          sebagai PENANDA (bukan latar tombol) untuk angka yang sedang jadi
          subjek keputusan, persis kategori yang DESIGN.md jatah sampai tiga
          kemunculan per layar, dan --accent-text yang ikut berbalik tema
          dipakai karena ini teks di atas --paper/--panel, bukan di atas
          latar aksen. */}
      <dl className="grid grid-cols-1 gap-space-2 text-label text-muted sm:grid-cols-2">
        <div>
          <dt className="font-medium text-ink">Tenggat pengajuan proposal</dt>
          <dd className={featured ? "font-semibold text-accent-text" : undefined}>
            {formatDate(campaign.apply_deadline)}
          </dd>
        </div>
        <div>
          <dt className="font-medium text-ink">Tenggat pendanaan</dt>
          <dd>{formatDate(campaign.funding_deadline)}</dd>
        </div>
      </dl>
      <Link
        href={`/jelajah/campaign/${campaign.id}`}
        className="inline-flex min-h-[44px] items-center text-body font-medium text-ink underline underline-offset-2"
      >
        Lihat campaign ini
      </Link>
    </article>
  );
}

type CampaignBrowseListState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: PublicCampaign[] };

// Daftar campaign publik di halaman jelajah, sisi UMKM dari layar yang sama
// tempat ProposalList (ProposalCard.tsx) melayani sisi investor.
//
// GAP BACKEND YANG DIKETAHUI: GET /campaigns (backend/app/services/campaign.py,
// list_campaigns) tidak memfilter status sama sekali, jadi campaign yang
// sudah "closed" ikut terkirim meski 10-api-contract.md menyiratkan daftar
// publik ini hanya yang open. Disaring di sini sebagai perbaikan sementara
// di sisi klien, BUKAN dianggap sudah beres: pemilik project akan menutup
// lubang ini di backend, dan filter klien ini boleh dibuang begitu itu terjadi.
export function CampaignBrowseList() {
  const [state, setState] = useState<CampaignBrowseListState>({ status: "loading" });

  async function load() {
    setState({ status: "loading" });
    try {
      const result = await api.get<{ items: PublicCampaign[] }>("/campaigns");
      const open = result.items.filter((campaign) => campaign.status === "open");
      setState({ status: "ready", items: open });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.",
      });
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (state.status === "loading") {
    return <LoadingState label="Memuat daftar campaign" minHeight={240} />;
  }
  if (state.status === "error") {
    return <ErrorState message={state.message} onRetry={load} />;
  }
  if (state.items.length === 0) {
    return (
      <EmptyState reason="Belum ada campaign yang terbuka untuk menerima proposal saat ini." />
    );
  }

  // Campaign dengan tenggat pengajuan paling dekat paling perlu diperhatikan
  // UMKM sekarang, jadi itulah yang mendapat perlakuan menonjol: hierarki
  // nyata dari data, sama seperti CampaignList di dashboard investor,
  // bukan urutan acak atau urutan mentah dari server.
  const urgentId = state.items.reduce((a, b) =>
    new Date(a.apply_deadline) < new Date(b.apply_deadline) ? a : b,
  ).id;

  return (
    <ol className="flex flex-col gap-space-3">
      {state.items.map((campaign, index) => (
        <li key={campaign.id} className="list-none">
          <CampaignBrowseCard campaign={campaign} featured={campaign.id === urgentId} index={index} />
        </li>
      ))}
    </ol>
  );
}
